from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, TypeAlias
from vm.builtins.code import PyConstant


if TYPE_CHECKING:
    from vm.function_ import FuncArgs
    from vm.builtins.pystr import PyStrRef
    from vm.builtins.pytype import PyTypeRef
    from vm.builtins.tuple import PyTupleRef, PyTupleTyped
    from vm.pyobject import PyContext
    from vm.pyobjectrc import PyObjectRef, PyRef
    from vm.builtins.code import PyCode
    from vm.builtins.dict import PyDictRef
    from vm.vm import VirtualMachine
import vm.pyobject as po
import vm.pyobjectrc as prc
import vm.types.slot as slot
import vm.builtins.pystr as pystr
import vm.frame as vframe
import vm.function.arguments as arguments
import vm.scope as vscope
import vm.builtins.asyncgenerator as pyasyncgenerator
import vm.builtins.generator as pygenerator
import vm.builtins.coroutine as pycoroutine
import bytecode.bytecode as bytecode
from common.deco import pymethod, pyproperty
from common.error import PyImplBase


@po.pyimpl(constructor=True)
@po.pyclass("cell")
@dataclass
class PyCell(po.PyClassImpl, slot.ConstructorMixin):
    contents: Optional[PyObjectRef]

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.cell_type

    @staticmethod
    def default() -> PyCell:
        return PyCell(None)

    @staticmethod
    def new(contents: Optional[PyObjectRef]) -> PyCell:
        return PyCell(contents)

    def set(self, value: Optional[PyObjectRef]) -> None:
        self.contents = value

    @pyproperty()
    def get_cell_contents(self, *, vm: VirtualMachine) -> PyObjectRef:
        if self.contents is None:
            vm.new_value_error("Cell is empty")
        else:
            return self.contents

    @pyproperty()
    def set_cell_contents(self, x: PyObjectRef, *, vm: VirtualMachine) -> None:
        self.set(x)

    # TODO: uncomment
    # @pyproperty()
    # def del_cell_contents(self, *, vm: VirtualMachine) -> None:
    #     self.set(None)

    @classmethod
    def py_new(
        cls, class_: PyTypeRef, fargs: FuncArgs, /, vm: VirtualMachine
    ) -> PyObjectRef:
        arg = fargs.bind(__pycell_py_new_args).arguments["value"]
        return PyCell.new(arg).into_pyresult_with_type(vm, class_)


PyCellRef: TypeAlias = "PyRef[PyCell]"


def __pycell_py_new_args(value: Optional[PyObjectRef] = None):
    ...


@po.tp_flags(has_dict=True, method_descr=True)
@po.pyimpl(get_descriptor=True, callable=True)
@po.pyclass("function")
@dataclass
class PyFunction(po.PyClassImpl, slot.CallableMixin, slot.GetDescriptorMixin):
    code: PyRef[PyCode]
    globals: PyDictRef
    closure: Optional[PyTupleTyped[PyCellRef]]
    defaults_and_kwdefaults: tuple[Optional[PyTupleRef], Optional[PyDictRef]]
    name: PyStrRef

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.function_type

    @staticmethod
    def new(
        code: PyRef[PyCode],
        globals: PyDictRef,
        closure: Optional[PyTupleTyped[PyCellRef]],
        defaults: Optional[PyTupleRef],
        kw_only_defaults: Optional[PyDictRef],
    ) -> PyFunction:
        name = code._.code.obj_name
        assert not isinstance(name, str), name
        return PyFunction(
            code=code,
            globals=globals,
            closure=closure,
            defaults_and_kwdefaults=(defaults, kw_only_defaults),
            name=name,
        )

    def fill_locals_from_args(
        self, frame: vframe.Frame, func_args: FuncArgs, vm: VirtualMachine
    ) -> None:
        code: bytecode.CodeObject[PyConstant, PyStrRef] = self.code._.code
        nargs = len(func_args.args)
        nexpected_args = code.arg_count
        total_args = code.arg_count + code.kwonlyarg_count

        fastlocals = frame.fastlocals

        args_iter = list(func_args.args)

        nargs_taken = min(nargs, nexpected_args)

        for i, arg in enumerate(args_iter[:nargs_taken]):
            fastlocals[i] = arg

        vararg_offset = total_args

        if bytecode.CodeFlags.HAS_VARARGS in code.flags:
            vararg_value = vm.ctx.new_tuple(args_iter[nargs:])
            fastlocals[vararg_offset] = vararg_value
            vararg_offset += 1
        else:
            if nargs > nexpected_args:
                vm.new_type_error(
                    "{}() takes {} positional arguments but {} were given".format(
                        code.obj_name, nexpected_args, nargs
                    )
                )

        if bytecode.CodeFlags.HAS_VARKEYWORDS in code.flags:
            d = vm.ctx.new_dict()
            fastlocals[vararg_offset] = d
            kwargs = d
        else:
            kwargs = None

        def argpos(r: range, name: str) -> Optional[int]:
            return next(
                (
                    p
                    for p, s in enumerate(code.varnames[r.start : r.stop], r.start)
                    if s._.as_str() == name
                    # if s == name
                ),
                None,
            )

        posonly_passed_as_kwarg = []
        for name, value in func_args.kwargs.items():
            if (
                pos := argpos(range(code.posonlyarg_count, total_args), name)
            ) is not None:
                slot = fastlocals[pos]
                if slot is not None:
                    vm.new_type_error(f"Got multiple values for argument '{name}'")
                fastlocals[pos] = value
            elif kwargs is not None:
                kwargs._.set_item(vm.ctx.new_str(name), value, vm)
            elif argpos(range(0, code.posonlyarg_count), name) is not None:
                posonly_passed_as_kwarg.append(name)
            else:
                vm.new_type_error(f"got an unexpected keyword argument '{name}'")

        if posonly_passed_as_kwarg:
            vm.new_type_error(
                "{}() got some positional-only arguments passed as keyword arguments: '{}'".format(
                    code.obj_name, ",".join(posonly_passed_as_kwarg)
                )
            )

        default_and_kwdefaults = None

        def get_defaults() -> tuple[Optional[PyTupleRef], Optional[PyDictRef]]:
            nonlocal default_and_kwdefaults
            if default_and_kwdefaults is not None:
                return default_and_kwdefaults
            else:
                default_and_kwdefaults = self.defaults_and_kwdefaults
                return default_and_kwdefaults

        if nargs < nexpected_args:
            if (v := get_defaults()[0]) is not None:
                defaults = v._.as_slice()
                ndefs = len(defaults)
            else:
                defaults = None
                ndefs = 0

            nrequired = code.arg_count - ndefs

            missing = [
                code.varnames[i]._.as_str()
                for i, x in ((i, fastlocals[i]) for i in range(nargs, nrequired))
                if x is None
            ]
            missing_args_len = len(missing)

            if missing:
                if len(missing) > 1:
                    last = missing.pop()
                    if len(missing) == 1:
                        and_ = "' and '"
                    else:
                        and_ = "', and '"
                    right = last
                else:
                    right, and_ = "", ""

                vm.new_type_error(
                    "{}() missing {} required positional argument{}: '{}{}{}'".format(
                        code.obj_name,
                        missing_args_len,
                        "" if missing_args_len == 1 else "s",
                        "', '".join(missing),
                        and_,
                        right,
                    )
                )

            if defaults is not None:
                for i in range(
                    max(0, min(nargs, nexpected_args) - nrequired), len(defaults)
                ):
                    if fastlocals[nrequired + i] is None:
                        fastlocals[nrequired + i] = defaults[i]

        if code.kwonlyarg_count > 0:
            for slot, kwarg, i in zip(
                fastlocals[code.arg_count :],
                code.varnames[code.arg_count :],
                range(code.kwonlyarg_count),
            ):
                if slot is not None:
                    continue

                if (defaults := get_defaults()[1]) is not None:
                    if (default := defaults._.get_item_opt(kwarg, vm)) is not None:
                        fastlocals[code.arg_count + i] = default

                vm.new_type_error(f"Missing required kw only argument: '{kwarg}'")

        if code.cell2arg is not None:
            for cell_idx, arg_idx in enumerate(code.cell2arg):
                if arg_idx == -1:
                    continue
                x = fastlocals[arg_idx]
                frame.cells_frees[cell_idx]._.set(x)

    def invoke_with_locals(
        self,
        func_args: FuncArgs,
        locals: Optional[arguments.ArgMapping],
        vm: VirtualMachine,
    ) -> PyObjectRef:
        code = self.code._.code
        if bytecode.CodeFlags.NEW_LOCALS in code.flags:
            locals = arguments.ArgMapping.from_dict_exact(vm.ctx.new_dict())
        elif locals is None:
            locals = arguments.ArgMapping.from_dict_exact(self.globals)

        if self.closure is None:
            closure = []
        else:
            closure = self.closure.as_slice()

        dict_ = vm.builtins.dict_()
        assert dict_ is not None  # FIXME?

        frame = vframe.Frame.new(
            code=self.code,
            scope=vscope.Scope.new(locals, self.globals),
            builtins=dict_,
            closure=closure,
            vm=vm,
        ).into_ref(vm)

        self.fill_locals_from_args(frame._, func_args, vm)

        is_gen = bytecode.CodeFlags.IS_GENERATOR in code.flags
        is_coro = bytecode.CodeFlags.IS_COROUTINE in code.flags
        if is_gen and not is_coro:
            return pygenerator.PyGenerator.new(frame, self.name).into_ref(vm)
        elif not is_gen and is_coro:
            return pycoroutine.PyCoroutine.new(frame, self.name).into_ref(vm)
        elif is_gen and is_coro:
            return pyasyncgenerator.PyAsyncGen.new(frame, self.name).into_ref(vm)
        else:
            return vm.run_frame_full(frame)

    def invoke(self, func_args: FuncArgs, vm: VirtualMachine) -> PyObjectRef:
        return self.invoke_with_locals(func_args, None, vm)

    @pyproperty()
    def get___code__(self, *, vm: VirtualMachine) -> PyRef[PyCode]:
        return self.code

    @pyproperty()
    def get___defaults__(self, *, vm: VirtualMachine) -> Optional[PyTupleRef]:
        return self.defaults_and_kwdefaults[0]

    @pyproperty()
    def set___defaults__(
        self, defaults: Optional[PyTupleRef], *, vm: VirtualMachine
    ) -> None:
        self.defaults_and_kwdefaults = (defaults, self.defaults_and_kwdefaults[1])

    @pyproperty()
    def get___kwdefaults__(self, *, vm: VirtualMachine) -> Optional[PyDictRef]:
        return self.defaults_and_kwdefaults[1]

    @pyproperty()
    def set___kwdefaults__(
        self, kwdefaults: Optional[PyDictRef], *, vm: VirtualMachine
    ) -> None:
        self.defaults_and_kwdefaults = (self.defaults_and_kwdefaults[0], kwdefaults)

    @pyproperty()
    def get___globals__(self, *, vm: VirtualMachine) -> PyDictRef:
        return self.globals

    @pyproperty()
    def get___closure__(self, *, vm: VirtualMachine) -> Optional[PyTupleRef]:
        if self.closure is None:
            return None
        return self.closure.tuple

    @pyproperty()
    def get___name__(self, *, vm: VirtualMachine) -> PyStrRef:
        return self.name

    @pyproperty()
    def set___name__(self, name: PyStrRef, /, *, vm: VirtualMachine) -> None:
        self.name = name

    @pymethod(True)
    @staticmethod
    def i__repr__(zelf: PyRef[PyFunction], *, vm: VirtualMachine) -> str:
        try:
            qualname_attr = zelf.as_object().get_attr(
                vm.ctx.new_str("__qualname__"), vm
            )
        except PyImplBase as _:
            qualname = None
        else:
            qualname = qualname_attr.downcast_ref(pystr.PyStr)
        if qualname is None:
            qualname = zelf._.name
        return "<function {} at {:#x}>".format(qualname._.as_str(), zelf.get_id())

    @classmethod
    def descr_get(
        cls,
        zelf: PyObjectRef,
        obj: Optional[PyObjectRef],
        class_: Optional[PyObjectRef],
        vm: VirtualMachine,
    ) -> PyObjectRef:
        raise NotImplementedError

    @classmethod
    def call(
        cls, zelf: PyRef[PyFunction], args: FuncArgs, vm: VirtualMachine
    ) -> PyObjectRef:
        return zelf._.invoke(args, vm)


@po.tp_flags(has_dict=True)
@po.pyimpl(callable=True, comparable=True, get_attr=True, constructor=True)
@po.pyclass("method")
@dataclass
class PyBoundMethod(po.PyClassImpl, slot.CallableMixin):
    object: PyObjectRef
    function: PyObjectRef

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.bound_method_type

    @staticmethod
    def new(object: PyObjectRef, function: PyObjectRef) -> PyBoundMethod:
        return PyBoundMethod(object=object, function=function)

    @staticmethod
    def new_ref(
        object: PyObjectRef, function: PyObjectRef, ctx: PyContext
    ) -> PyRef[PyBoundMethod]:
        assert isinstance(function, prc.PyRef)
        return prc.PyRef.new_ref(
            PyBoundMethod(object, function), ctx.types.bound_method_type, None
        )

    @classmethod
    def call(
        cls, zelf: PyRef[PyBoundMethod], args: FuncArgs, vm: VirtualMachine
    ) -> PyObjectRef:
        args.prepend_arg(zelf._.object)
        return vm.invoke(zelf._.function, args)

    # TODO: impl Comparable for PyBoundMethod
    # TODO: impl GetAttr for PyBoundMethod
    # TODO: impl Constructor for PyBoundMethod
    # TODO: impl PyBoundMethod @ 506


def init(context: PyContext) -> None:
    PyFunction.extend_class(context, context.types.function_type)
    PyBoundMethod.extend_class(context, context.types.bound_method_type)
    PyCell.extend_class(context, context.types.cell_type)
