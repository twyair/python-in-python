from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, TypeAlias

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


@po.pyimpl(constructor=True)
@po.pyclass("cell")
@dataclass
class PyCell(po.PyClassImpl):
    contents: Optional[PyObjectRef]

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.cell_type

    @staticmethod
    def default() -> PyCell:
        return PyCell(None)

    def into_ref(self, vm: VirtualMachine) -> PyCellRef:
        return PyRef[PyCell](vm.ctx.types.cell_type, None, self)

    def set(self, value: Optional[PyObjectRef]) -> None:
        self.contents = value

    # TODO: impl Constructor for PyCell


PyCellRef: TypeAlias = "PyRef[PyCell]"


@po.tp_flags(has_dict=True, method_descr=True)
@po.pyimpl(get_descriptor=True, callable=True)
@po.pyclass("function")
@dataclass
class PyFunction(po.PyClassImpl):
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
        return PyFunction(
            code=code,
            globals=globals,
            closure=closure,
            defaults_and_kwdefaults=(defaults, kw_only_defaults),
            name=name,
        )

    def into_object(self: PyFunction, vm: VirtualMachine) -> PyRef[PyFunction]:
        return prc.PyRef.new_ref(self, vm.ctx.types.function_type, None)

    # TODO: impl PyFunction @ 334
    # TODO: impl GetDescriptor for PyFunction
    # TODO: impl Callable for PyFunction


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
