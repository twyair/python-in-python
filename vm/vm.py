from __future__ import annotations

import enum
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import (
    Any,
    Callable,
    NoReturn,
    Optional,
    Sequence,
    Type,
    TypeAlias,
    TypeVar,
    TYPE_CHECKING,
)


if TYPE_CHECKING:
    from vm.pyobject import PyContext, PyMethod
    from vm.pyobjectrc import PT, PyObject, PyObjectRef, PyRef
    from vm.builtins.code import PyCode
    from vm.builtins.dict import PyDictRef
    from vm.builtins.int import PyInt, PyIntRef
    from vm.builtins.list import PyList
    from vm.builtins.module import PyModule
    from vm.builtins.pystr import PyStr, PyStrRef
    from vm.builtins.pytype import PyType, PyTypeRef
    from vm.builtins.tuple import PyTuple, PyTupleRef, PyTupleTyped
    from vm.codecs import CodecsRegistry
    from vm.exceptions import PyBaseException, PyBaseExceptionRef
    from vm.frame import ExecutionResult, FrameRef
    from vm.function.arguments import ArgMapping
    from vm.function_ import FuncArgs
    from vm.protocol.iter import PyIterIter, PyIterReturnReturn

import vm.pyobject as po
import vm.pyobjectrc as prc
import vm.scope as scope
import vm.types.slot as slot
import vm.frozen as frozen
import vm.signal as signal
import vm.stdlib as stdlib
import vm.stdlib.builtins as std_builtins
import vm.stdlib.sys as std_sys
import vm.codecs as codecs
import vm.builtins.module as pymodule
import vm.frame as vm_frame
import vm.exceptions as vm_exceptions
import vm.function_ as vm_function_
import vm.builtins.object as pyobject
import vm.builtins.module as pymodule
import vm.builtins.int as pyint

from bytecode.bytecode import CodeObject, FrozenModule
from common.error import PyImplBase, PyImplError, PyImplException
from common.hash import HashSecret
from compiler.compile import CompileError, CompileErrorType, CompileOpts
from compiler.mode import Mode
from compiler.porcelain import compile as compile_

MAX_LENGTH_HINT = 2 << 32  # FIXME? `isize::max_value()`


@dataclass
class VirtualMachine:
    builtins: PyRef[PyModule]
    sys_module: PyRef[PyModule]
    ctx: PyContext
    frames: list[FrameRef]
    wasm_id: Optional[str]
    exceptions: ExceptionStack
    import_func: PyObjectRef
    profile_func: PyObjectRef
    trace_func: PyObjectRef
    use_tracing: bool
    recursion_limit: int
    signal_handlers: Optional[list[Optional[PyObjectRef]]]  # signal.NSIG elements
    signal_rx: Optional[signal.UserSignalReceiver]
    repr_guards: set[int]
    state: PyGlobalState
    initialized: bool
    recursion_depth: int

    @staticmethod
    def new(settings: PySettings) -> VirtualMachine:
        ctx = po.PyContext.new()

        new_module = lambda: prc.PyRef.new_ref(
            pymodule.PyModule(), ctx.types.module_type, ctx.new_dict()
        )

        builtins = new_module()
        sys_module = new_module()

        import_func = ctx.get_none()
        profile_func = ctx.get_none()
        trace_func = ctx.get_none()

        NONE: Optional[PyObjectRef] = None
        SIGNAL_HANDLERS: list[Optional[PyObjectRef]] = [NONE] * signal.NSIG  # type: ignore
        signal_handlers: Optional[list[Optional[PyObjectRef]]] = SIGNAL_HANDLERS.copy()

        module_inits = stdlib.get_module_inits()

        if settings.hash_seed is None:
            hash_secret = HashSecret.random()
        else:
            hash_secret = HashSecret.new(settings.hash_seed)

        codec_registry = codecs.CodecsRegistry.new(ctx)

        vm = VirtualMachine(
            builtins=builtins,
            sys_module=sys_module,
            ctx=ctx,
            frames=[],
            wasm_id=None,
            exceptions=ExceptionStack(None, None),
            import_func=import_func,
            profile_func=profile_func,
            trace_func=trace_func,
            use_tracing=False,
            recursion_limit=1000,
            signal_handlers=signal_handlers,  # type: ignore FIXME?
            signal_rx=None,
            repr_guards=set(),
            state=PyGlobalState(
                settings,
                module_inits,
                frozen={},
                stack_size=0,
                thread_count=0,
                hash_secret=hash_secret,
                atexit_funcs=[],
                codec_registry=codec_registry,
            ),
            initialized=False,
            recursion_depth=0,
        )

        vm.state.frozen = dict(frozen.map_frozen(vm, frozen.get_module_inits()))

        vm.builtins._.init_module_dict(
            vm.ctx.new_str("builtins"), vm.ctx.get_none(), vm
        )
        vm.sys_module._.init_module_dict(vm.ctx.new_str("sys"), vm.ctx.get_none(), vm)

        return vm

    def initialize(self, initialize_parameter: InitParameter) -> None:
        assert not self.initialized, "Double Initialize Error"

        std_builtins.make_module(self, self.builtins)
        std_sys.init_module(self, self.sys_module, self.builtins)

        # TODO:
        # raise NotImplementedError

        self.initialized = True

    # TODO: move
    def mk_str(self, s: str) -> PyStrRef:
        import vm.builtins.pystr as pystr

        return pystr.PyStr.from_str(s, self.ctx)

    def check_signals(self) -> None:
        # TODO
        pass

    def run_code_object(self, code: PyRef[PyCode], scope: scope.Scope) -> PyResult:
        assert self.builtins.dict is not None
        frame = vm_frame.Frame.new(
            code, scope, self.builtins.dict.d, [], self
        ).into_ref(self)
        return self.run_frame_full(frame)

    def run_frame_full(self, frame: FrameRef) -> PyResult:
        res = self.run_frame(frame)
        assert isinstance(
            res, vm_frame.ExecutionResultReturn
        ), "Got unexpected result from function"
        return res.value

    def current_recursion_depth(self) -> int:
        return self.recursion_depth

    def with_recursion(self, where: str, f: Callable[[], R]) -> R:
        self.check_recursive_call(where)
        self.recursion_depth += 1
        result = f()
        self.recursion_depth -= 1
        return result

    def with_frame(self, frame: FrameRef, f: Callable[[FrameRef], R]) -> R:
        def do():
            self.frames.append(frame)
            result = f(frame)
            self.frames.pop()
            return result

        return self.with_recursion("", do)

    def run_frame(self, frame: FrameRef) -> ExecutionResult:
        return self.with_frame(frame, lambda f: f._.run(self))

    def check_recursive_call(self, where: str) -> None:
        if self.recursion_depth >= self.recursion_limit:
            self.new_recursion_error(f"maximum recursion depth exceeded {where}")

    def current_frame(self) -> Optional[FrameRef]:
        if not self.frames:
            return None
        else:
            return self.frames[-1]

    def current_locals(self) -> ArgMapping:
        frame = self.current_frame()
        assert frame is not None, "called current_locals but no frames on the stack"
        return frame._.get_locals(self)

    def current_globals(self) -> PyDictRef:
        frame = self.current_frame()
        assert frame is not None, "called current_globals but no frames on the stack"
        return frame._.globals

    def try_class(self, module: str, class_: str) -> PyTypeRef:
        res = (
            self.import_(self.mk_str(module), None, 0)
            .get_attr(self.mk_str(class_), self)
            .downcast(PyType)
        )
        assert res is not None, "not a class"
        return res

    def class_(self, module: str, class_: str) -> PyTypeRef:
        module_ = self.import_(self.mk_str(module), None, 0)
        result = module_.get_attr(self.mk_str(class_), self)
        result = result.downcast(PyType)
        assert result is not None, "not a class"
        return result

    def new_scope_with_builtins(self) -> scope.Scope:
        return scope.Scope.with_builtins(None, self.ctx.new_dict(), self)

    def new_pyobj(self, value: Any) -> PyObjectRef:
        return value.into_pyobj(self)

    def new_tuple(self, value: Sequence[PyObjectRef]) -> PyTupleRef:
        return self.ctx.new_tuple(list(value))

    def is_none(self, obj: PyObject) -> bool:
        return obj.is_(self.ctx.none)

    def unwrap_or_none(self, obj: Optional[PyObjectRef]) -> PyObjectRef:
        if obj is None:
            return self.ctx.get_none()
        return obj

    def generic_getattribute_opt(
        self,
        obj: PyObjectRef,
        name_str: PyStrRef,
        dict_: Optional[PyDictRef],
    ) -> Optional[PyObjectRef]:
        name = name_str._.as_str()
        obj_cls = obj.class_()

        if (descr := obj_cls.get_attr(self.mk_str(name), self)) is not None:
            descr_cls = descr.class_()
            descr_get = descr_cls._.mro_find_map(lambda cls: cls.slots.descr_get)
            if descr_get is not None:
                if (
                    descr_cls._.mro_find_map(lambda cls: cls.slots.descr_set)
                    is not None
                ):
                    return descr_get(descr, obj, obj_cls, self)
            cls_attr = (descr, descr_get)
        else:
            cls_attr = None

        if dict_ is None and obj.dict is not None:
            dict_ = obj.dict.d

        if dict_ is not None:
            attr = dict_._.get_item_opt(self.mk_str(name), self)
            if attr is not None:
                return attr

        if cls_attr is not None:
            attr, descr_get = cls_attr
            if descr_get is not None:
                return descr_get(attr, obj, obj_cls, self)
            else:
                return attr
        elif getter := obj_cls.get_attr(self.mk_str("__getattr__"), self):
            return self.invoke(getter, vm_function_.FuncArgs([obj, name_str]))
        else:
            return None

    def generic_getattribute(self, obj: PyObjectRef, name: PyStrRef) -> PyObjectRef:
        res = self.generic_getattribute_opt(obj, name, None)
        if res is None:
            self.new_attribute_error(f"{obj} has no attribute '{name}'")
        return res

    def invoke(self, func: PyObject, args: FuncArgs) -> PyObjectRef:
        return self._invoke(func, args.into_args(self))

    def _invoke(self, callable: PyObject, args: FuncArgs) -> PyObjectRef:
        slot_call = callable.class_()._.mro_find_map(lambda cls: cls.slots.call)
        if slot_call is not None:
            return slot_call(callable, args, self)
        else:
            self.new_type_error(
                f"'{callable.class_()._.name()}' object is not callable"
            )

    def invoke_exception(
        self, cls: PyTypeRef, args: list[PyObjectRef]
    ) -> PyBaseExceptionRef:
        res = self.invoke(cls.as_object(), FuncArgs(args, OrderedDict()))
        return PyBaseExceptionRef.try_from_object(PyBaseException, self, res)

    def normalize_exception(
        self, exc_type: PyObjectRef, exc_val: PyObjectRef, exc_tb: PyObjectRef
    ) -> PyBaseExceptionRef:
        raise NotImplementedError

    def is_callable(self, obj: PyObject) -> bool:
        return obj.class_()._.mro_find_map(lambda cls: cls.slots.call) is not None

    def extract_elements_as_pyobjects(self, value: PyObject) -> list[PyObjectRef]:
        return self.extract_elements_func(value, lambda obj: obj)

    def extract_elements(self, t: Type[PT], value: PyObject) -> list[PT]:
        return self.extract_elements_func(
            value, lambda obj: t.try_from_object(self, obj)
        )

    def extract_elements_func(
        self, value: PyObject, func: Callable[[PyObjectRef], R]
    ) -> list[R]:
        cls = value.class_()
        if cls.is_(self.ctx.types.tuple_type):
            return [func(obj) for obj in value.payload_unchecked(PyTuple).as_slice()]
        elif cls.is_(self.ctx.types.list_type):
            return [func(obj) for obj in value.payload_unchecked(PyList).elements]
        else:
            return self.map_pyiter(value, func)

    def map_pyiter(self, value: PyObject, f: Callable[[PyObjectRef], R]) -> list[R]:
        iter_ = value.get_iter(self)
        cap = None
        try:
            cap = self.length_hint_opt(value)
        except PyImplException as e:
            if e.exception.class_().is_(self.ctx.exceptions.runtime_error):
                raise

        if cap is not None and cap >= MAX_LENGTH_HINT:
            return []

        # FIXME!
        return PyIterIter.new(self, iter_.as_ref(), cap).map(f)

    def check_signal(self) -> None:
        signal.check_signals(self)

    def compile_opts(self) -> CompileOpts:
        return CompileOpts(self.state.settings.optimize)

    def compile(self, source: str, mode: Mode, source_path: str) -> PyRef[PyCode]:
        return self.compile_with_opts(source, mode, source_path, self.compile_opts())

    def compile_with_opts(
        self, source: str, mode: Mode, source_path: str, opts: CompileOpts
    ) -> PyRef[PyCode]:
        import vm.builtins.code as pycode

        return pycode.PyCode(
            self.map_codeobj(compile_(source, mode, source_path, opts))
        ).into_ref(self)

    def get_attribute_opt(
        self, obj: PyObjectRef, attr_name: PyStrRef
    ) -> Optional[PyObjectRef]:
        try:
            return obj.get_attr(attr_name, self)
        except PyImplException as e:
            if e.exception.isinstance(self.ctx.exceptions.attribute_error):
                return None
            raise

    def get_method(self, obj: PyObjectRef, method_name: str) -> Optional[PyObjectRef]:
        method = obj.get_class_attr(method_name)
        if method is None:
            return None
        return self.call_if_get_descriptor(method, obj)

    def get_special_method(self, obj: PyObjectRef, method: str) -> PyMethod:
        return po.PyMethod.get_special(obj, method, self)

    def call_method(
        self, obj: PyObject, method_name: str, args: FuncArgs
    ) -> PyObjectRef:
        return po.PyMethod.get(obj, self.mk_str(method_name), self).invoke(args, self)

    def call_get_descriptor_specific(
        self, descr: PyObjectRef, obj: Optional[PyObjectRef], cls: PyObjectRef
    ) -> PyObjectRef:
        descr_get = descr.class_()._.mro_find_map(lambda cls: cls.slots.descr_get)
        if descr_get is not None:
            return descr_get(descr, obj, cls, self)
        else:
            raise PyImplError(descr)

    def call_get_descriptor(self, descr: PyObjectRef, obj: PyObjectRef) -> PyObjectRef:
        cls = obj.clone_class().into_pyobj(self)
        return self.call_get_descriptor_specific(descr, obj, cls)

    def call_if_get_descriptor(
        self, attr: PyObjectRef, obj: PyObjectRef
    ) -> PyObjectRef:
        try:
            return self.call_get_descriptor(attr, obj)
        except PyImplError as e:
            return e.obj

    def call_special_method(
        self, obj: PyObjectRef, method: str, args: FuncArgs
    ) -> PyResult:
        return self.get_special_method(obj, method).invoke(args, self)

    def to_index_opt(self, obj: PyObjectRef) -> Optional[PyIntRef]:
        try:
            return obj.downcast(pyint.PyInt)
        except PyImplError as e:
            index = self.get_method(e.obj, "__index__")
            if index is None:
                return None
            index = self.invoke(index, vm_function_.FuncArgs.empty())
            try:
                return index.downcast(pyint.PyInt)
            except PyImplError as e:
                self.new_type_error(
                    f"__index__ returned non-int (type {e.obj.class_()._.name()})"
                )
        return None

    def to_index(self, obj: PyObject) -> PyIntRef:
        index = self.to_index_opt(obj)
        if index is not None:
            return index
        self.new_type_error(
            f"'{obj.class_()._.name()}' object cannot be interpreted as an integer"
        )

    def import_(
        self, module: PyStrRef, from_list: Optional[PyTupleTyped[PyStrRef]], level: int
    ) -> PyObjectRef:
        return self._import_inner(module, from_list, level)

    def _import_inner(
        self, module: PyStrRef, from_list: Optional[PyTupleTyped[PyStrRef]], level: int
    ) -> PyObjectRef:
        weird = (
            "." in module._.as_str()
            or level != 0
            or from_list is not None
            and not from_list.is_empty()
        )

        if not weird:
            sys_modules = self.sys_module.get_attr(self.mk_str("modules"), self)
            cached_module = sys_modules.get_item(module, self)
            if self.is_none(cached_module):
                self.new_import_error(
                    f"import of {module} halted; None in sys.modules", module
                )
            else:
                return cached_module
        else:
            try:
                import_func = self.builtins.get_attr(self.mk_str("__import__"), self)
            except PyImplBase:
                self.new_import_error("__import__ not found", module)
            locals, globals = None, None
            if (frame := self.current_frame()) is not None:
                locals = frame._.locals
                globals = frame._.globals
            if from_list is None:
                from_list_ = self.new_tuple(())
            else:
                from_list_ = from_list.into_pyobject(self)
            return self.invoke(
                # FIXME
                import_func,
                vm_function_.FuncArgs(
                    [
                        module,
                        globals if globals is not None else self.ctx.get_none(),
                        locals.obj if locals is not None else self.ctx.get_none(),
                        from_list_,
                        PyInt(level).into_ref(self),
                    ]
                ),
            )
            # TODO: .map_err(|exc| import::remove_importlib_frames(self, &exc))

    def call_or_unsupported(
        self,
        obj: PyObject,
        arg: PyObject,
        method: str,
        unsupported: Callable[[VirtualMachine, PyObject, PyObject], PyObjectRef],
    ) -> PyObjectRef:
        if (method_ := self.get_method(obj, method)) is not None:
            result = po.PyArithmeticValue.from_object(
                self, self.invoke(method_, vm_function_.FuncArgs([arg]))
            )
            if result.value is not None:
                return result.value
        return unsupported(self, obj, arg)

    def call_or_reflection(
        self,
        lhs: PyObject,
        rhs: PyObject,
        default: str,
        reflection: str,
        unsupported: Callable[[VirtualMachine, PyObject, PyObject], PyObjectRef],
    ) -> PyObjectRef:
        def do(vm: VirtualMachine, lhs: PyObject, rhs: PyObject) -> PyObjectRef:
            if not lhs.class_().is_(rhs.class_()):
                return vm.call_or_unsupported(
                    rhs, lhs, reflection, lambda _, rhs, lhs: unsupported(vm, lhs, rhs)
                )
            else:
                return unsupported(vm, lhs, rhs)

        return self.call_or_unsupported(lhs, rhs, default, do)

    def new_exception(
        self,
        exc_type: PyTypeRef,
        args: list[PyObjectRef],
        attrs: Optional[dict[str, PyObjectRef]] = None,
    ) -> NoReturn:
        exc = prc.PyRef.new_ref(
            vm_exceptions.PyBaseException.new(args, self), exc_type, self.ctx.new_dict()
        )
        if attrs is not None:
            for k, v in attrs.items():
                exc.as_object().set_attr(self.mk_str(k), v, self)
        raise PyImplException(exc)

    def new_exception_empty(
        self, exc_type: PyTypeRef, attrs: Optional[dict[str, PyObjectRef]] = None
    ) -> NoReturn:
        self.new_exception(exc_type, [], attrs)

    def new_exception_msg(
        self,
        exc_type: PyTypeRef,
        msg: str,
        attrs: Optional[dict[str, PyObjectRef]] = None,
    ) -> NoReturn:
        self.new_exception(exc_type, [self.ctx.new_str(msg)], attrs)

    def new_lookup_error(self, msg: str) -> NoReturn:
        self.new_exception_msg(self.ctx.exceptions.lookup_error, msg)

    def new_attribute_error(self, msg: str) -> NoReturn:
        self.new_exception_msg(self.ctx.exceptions.attribute_error, msg)

    def new_type_error(self, msg: str) -> NoReturn:
        self.new_exception_msg(self.ctx.exceptions.type_error, msg)

    def new_name_error(self, msg: str, name: PyStrRef) -> NoReturn:
        self.new_exception_msg(self.ctx.exceptions.name_error, msg, {"name": name})

    def new_unsupported_unary_error(self, a: PyObject, op: str) -> NoReturn:
        self.new_type_error(f"bad operand type for {op}: '{a.class_()._.name()}'")

    def new_unsupported_binop_error(
        self, a: PyObject, b: PyObject, op: str
    ) -> NoReturn:
        self.new_type_error(
            f"'{op}' not supported between instances of '{a.class_()._.name()}' and '{b.class_()._.name()}'"
        )

    def new_unsupported_ternop_error(
        self, a: PyObject, b: PyObject, c: PyObject, op: str
    ) -> NoReturn:
        self.new_type_error(
            f"Unsupported operand types for '{op}': '{a.class_()._.name()}', '{b.class_()._.name()}' and '{c.class_()._.name()}'"
        )

    def new_os_error(self, msg: str) -> NoReturn:
        self.new_exception_msg(self.ctx.exceptions.os_error, msg)

    def new_unicode_decode_error(self, msg: str) -> NoReturn:
        self.new_exception_msg(self.ctx.exceptions.unicode_decode_error, msg)

    def new_unicode_encode_error(self, msg: str) -> NoReturn:
        self.new_exception_msg(self.ctx.exceptions.unicode_encode_error, msg)

    def new_value_error(self, msg: str) -> NoReturn:
        self.new_exception_msg(self.ctx.exceptions.value_error, msg)

    def new_buffer_error(self, msg: str) -> NoReturn:
        self.new_exception_msg(self.ctx.exceptions.buffer_error, msg)

    def new_key_error(self, obj: PyObjectRef) -> NoReturn:
        self.new_exception(self.ctx.exceptions.key_error, [obj])

    def new_index_error(self, msg: str) -> NoReturn:
        self.new_exception_msg(self.ctx.exceptions.index_error, msg)

    def new_recursion_error(self, msg: str) -> NoReturn:
        self.new_exception_msg(self.ctx.exceptions.recursion_error, msg)

    def new_zero_division_error(self, msg: str) -> NoReturn:
        self.new_exception_msg(self.ctx.exceptions.zero_division_error, msg)

    def new_overflow_error(self, msg: str) -> NoReturn:
        self.new_exception_msg(self.ctx.exceptions.overflow_error, msg)

    def new_syntax_error(self, error: CompileError) -> NoReturn:
        syntax_error_type = self.ctx.exceptions.syntax_error
        if error.error == CompileErrorType.PARSE:
            if error.args[0].is_indentation_error():
                syntax_error_type = self.ctx.exceptions.indentation_error
            elif error.args[0].is_tab_error():
                syntax_error_type = self.ctx.exceptions.tab_error
        assert error.location is not None
        lineno = self.ctx.new_int(error.location.lineno)
        offset = self.ctx.new_int(error.location.col_offset)
        # FIXME:
        # text = error.statement.into_pyobject(self)
        text = self.ctx.new_str("")
        filename = self.ctx.new_str(error.source_path)
        self.new_exception_msg(
            syntax_error_type,
            error.to_string(),
            {"lineno": lineno, "offset": offset, "filename": filename, "text": text},
        )

    def new_import_error(self, msg: str, name: PyStrRef) -> NoReturn:
        self.new_exception_msg(self.ctx.exceptions.import_error, msg, {"name": name})

    def new_runtime_error(self, msg: str) -> NoReturn:
        self.new_exception_msg(self.ctx.exceptions.runtime_error, msg)

    def new_memory_error(self, msg: str) -> NoReturn:
        self.new_exception_msg(self.ctx.exceptions.memory_error, msg)

    def new_stop_iteration(self, value: Optional[PyObjectRef]) -> NoReturn:
        if value is not None:
            args = [value]
        else:
            args = []
        self.new_exception(self.ctx.exceptions.stop_iteration, args)

    def _binop_generic(
        self, a: PyObject, b: PyObject, op: str, name: str
    ) -> PyObjectRef:
        return self.call_or_reflection(
            a,
            b,
            f"__{name}__",
            f"__r{name}__",
            lambda vm, a, b: vm.new_unsupported_binop_error(a, b, op),
        )

    def _sub(self, a: PyObject, b: PyObject) -> PyObjectRef:
        return self._binop_generic(a, b, "-", "sub")

    def _add(self, a: PyObject, b: PyObject) -> PyObjectRef:
        return self._binop_generic(a, b, "+", "add")

    def _mul(self, a: PyObject, b: PyObject) -> PyObjectRef:
        return self._binop_generic(a, b, "*", "mul")

    def _matmul(self, a: PyObject, b: PyObject) -> PyObjectRef:
        return self._binop_generic(a, b, "@", "matmul")

    def _truediv(self, a: PyObject, b: PyObject) -> PyObjectRef:
        return self._binop_generic(a, b, "/", "truediv")

    def _floordiv(self, a: PyObject, b: PyObject) -> PyObjectRef:
        return self._binop_generic(a, b, "//", "floordiv")

    def _pow(self, a: PyObject, b: PyObject) -> PyObjectRef:
        return self._binop_generic(a, b, "**", "pow")

    def _mod(self, a: PyObject, b: PyObject) -> PyObjectRef:
        return self._binop_generic(a, b, "%", "mod")

    def _divmod(self, a: PyObject, b: PyObject) -> PyObjectRef:
        return self._binop_generic(a, b, "divmod", "divmod")

    def _lshift(self, a: PyObject, b: PyObject) -> PyObjectRef:
        return self._binop_generic(a, b, "<<", "lshift")

    def _rshift(self, a: PyObject, b: PyObject) -> PyObjectRef:
        return self._binop_generic(a, b, ">>", "rshift")

    def _xor(self, a: PyObject, b: PyObject) -> PyObjectRef:
        return self._binop_generic(a, b, "^", "xor")

    def _or(self, a: PyObject, b: PyObject) -> PyObjectRef:
        return self._binop_generic(a, b, "|", "or")

    def _and(self, a: PyObject, b: PyObject) -> PyObjectRef:
        return self._binop_generic(a, b, "&", "and")

    def _binop_inplace_generic(
        self, a: PyObject, b: PyObject, name: str, op: str
    ) -> PyObjectRef:
        return self.call_or_unsupported(
            a,
            b,
            f"__i{name}__",
            lambda vm, a, b: vm.call_or_reflection(
                a,
                b,
                f"__{name}__",
                f"__r{name}__",
                lambda vm, a, b: vm.new_unsupported_binop_error(a, b, f"{op}="),
            ),
        )

    def _isub(self, a: PyObject, b: PyObject) -> PyObjectRef:
        return self._binop_inplace_generic(a, b, "-", "sub")

    def _iadd(self, a: PyObject, b: PyObject) -> PyObjectRef:
        return self._binop_inplace_generic(a, b, "+", "add")

    def _imul(self, a: PyObject, b: PyObject) -> PyObjectRef:
        return self._binop_inplace_generic(a, b, "*", "mul")

    def _imatmul(self, a: PyObject, b: PyObject) -> PyObjectRef:
        return self._binop_inplace_generic(a, b, "@", "matmul")

    def _itruediv(self, a: PyObject, b: PyObject) -> PyObjectRef:
        return self._binop_inplace_generic(a, b, "/", "truediv")

    def _ifloordiv(self, a: PyObject, b: PyObject) -> PyObjectRef:
        return self._binop_inplace_generic(a, b, "//", "floordiv")

    def _ipow(self, a: PyObject, b: PyObject) -> PyObjectRef:
        return self._binop_inplace_generic(a, b, "**", "pow")

    def _imod(self, a: PyObject, b: PyObject) -> PyObjectRef:
        return self._binop_inplace_generic(a, b, "%", "mod")

    def _ilshift(self, a: PyObject, b: PyObject) -> PyObjectRef:
        return self._binop_inplace_generic(a, b, "<<", "lshift")

    def _irshift(self, a: PyObject, b: PyObject) -> PyObjectRef:
        return self._binop_inplace_generic(a, b, ">>", "rshift")

    def _ixor(self, a: PyObject, b: PyObject) -> PyObjectRef:
        return self._binop_inplace_generic(a, b, "^", "xor")

    def _ior(self, a: PyObject, b: PyObject) -> PyObjectRef:
        return self._binop_inplace_generic(a, b, "|", "or")

    def _iand(self, a: PyObject, b: PyObject) -> PyObjectRef:
        return self._binop_inplace_generic(a, b, "&", "and")

    def _abs(self, a: PyObject) -> PyObjectRef:
        # TODO: .map_err(|_| self.new_unsupported_unary_error(a, "abs()"))?
        return self.get_special_method(a, "__abs__").invoke(
            vm_function_.FuncArgs.empty(), self
        )

    def _pos(self, a: PyObject) -> PyObjectRef:
        return self.get_special_method(a, "__pos__").invoke(
            vm_function_.FuncArgs.empty(), self
        )

    def _neg(self, a: PyObject) -> PyObjectRef:
        return self.get_special_method(a, "__neg__").invoke(
            vm_function_.FuncArgs.empty(), self
        )

    def _invert(self, a: PyObject) -> PyObjectRef:
        return self.get_special_method(a, "__invert__").invoke(
            vm_function_.FuncArgs.empty(), self
        )

    def _membership_iter_search(
        self, haystack: PyObjectRef, needle: PyObjectRef
    ) -> PyIntRef:
        iter = haystack.get_iter(self)
        while isinstance((v := iter.next(self)), PyIterReturnReturn):
            if self.bool_eq(needle, v.value):
                return self.ctx.new_bool(True)
            else:
                continue
        return self.ctx.new_bool(False)

    def _membership(self, haystack: PyObjectRef, needle: PyObjectRef) -> PyObjectRef:
        try:
            method = PyMethod.get_special(haystack, "__contains__", self)
        except PyImplError as err:
            return self._membership_iter_search(err.obj, needle)
        else:
            return method.invoke(vm_function_.FuncArgs([needle], OrderedDict()), self)

    def push_exception(self, exc: Optional[PyBaseExceptionRef]) -> None:
        self.exceptions.prev = self.exceptions
        self.exceptions.exc = exc

    def pop_exception(self) -> Optional[PyBaseExceptionRef]:
        res = self.exceptions.exc
        assert (
            self.exceptions.prev is not None
        ), "pop_exception() without nested exc stack"
        self.exceptions = self.exceptions.prev
        return res

    def take_exception(self) -> Optional[PyBaseExceptionRef]:
        res = self.exceptions.exc
        self.exceptions.exc = None
        return res

    def current_exception(self) -> Optional[PyBaseExceptionRef]:
        return self.exceptions.exc

    def set_exception(self, exc: Optional[PyBaseExceptionRef]) -> None:
        self.exceptions.exc = exc

    def contextualize_exception(self, exception: PyBaseExceptionRef) -> None:
        context_exc = self.topmost_exception()
        if context_exc is not None:
            if not context_exc.is_(exception):
                o = context_exc  # FIXME: `.clone()`
                while (context := o._.context) is not None:
                    if context.is_(exception):
                        # o.set_context(None)  # TODO: ???
                        break
                    o = context
                exception._.context = context_exc

    def topmost_exception(self) -> Optional[PyBaseExceptionRef]:
        cur = self.exceptions
        while cur is not None:
            if cur.exc is not None:
                return cur.exc
            cur = cur.prev
        return None

    def bool_eq(self, a: PyObject, b: PyObject) -> bool:
        return a.rich_compare_bool(b, slot.PyComparisonOp.Eq, self)

    def identical_or_equal(self, a: PyObject, b: PyObject) -> bool:
        return a.is_(b) or self.bool_eq(a, b)

    def bool_seq_lt(self, a: PyObject, b: PyObject) -> Optional[bool]:
        if a.rich_compare_bool(b, slot.PyComparisonOp.Lt, self):
            return True
        elif not self.bool_eq(a, b):
            return False
        else:
            return None

    def bool_seq_gt(self, a: PyObject, b: PyObject) -> Optional[bool]:
        if a.rich_compare_bool(b, slot.PyComparisonOp.Gt, self):
            return True
        elif not self.bool_eq(a, b):
            return False
        else:
            return None

    def map_codeobj(self, code: CodeObject) -> CodeObject:
        # FIXME
        return code

    # original name: `__module_set_attr`
    def module_set_attr(
        self, module: PyObject, attr_name: PyStrRef, attr_value: PyObjectRef
    ) -> None:
        pyobject.generic_setattr(module, attr_name, attr_value, self)

    def new_module(self, name: str, dict: PyDictRef, doc: Optional[str]) -> PyObjectRef:
        module = prc.PyRef.new_ref(
            pymodule.PyModule(), self.ctx.types.module_type, dict
        )
        module._.init_module_dict(
            self.mk_str(name),
            self.mk_str(doc) if doc is not None else self.ctx.get_none(),
            self,
        )
        return module

    def length_hint_opt(self, iter: PyObjectRef) -> Optional[int]:
        try:
            return iter.length(self)
        except PyImplException as e:
            if not e.exception.isinstance(self.ctx.exceptions.type_error):
                raise

        hint_method = self.get_method(iter, "__length_hint__")
        if hint_method is None:
            return None

        try:
            result = self.invoke(hint_method, vm_function_.FuncArgs())
        except PyImplException as e:
            if e.exception.isinstance(self.ctx.exceptions.type_error):
                return None
            else:
                raise
        else:
            if result.is_(self.ctx.not_implemented):
                return None

        hint = result.payload_if_subclass(PyInt, self)
        if hint is None:
            self.new_type_error(
                f"'{result.class_()._.name()}' object cannot be interpreted as an integer"
            )

        hint_i = hint.as_int()
        if hint_i < 0:
            self.new_value_error("__length_hint__() should return >= 0")
        return hint_i

    def exception_args_as_string(
        self, varargs: PyTupleRef, str_single: bool
    ) -> list[PyStrRef]:
        def get_repr(a: PyObjectRef) -> PyStrRef:
            try:
                return a.repr(self)
            except PyImplBase as _:
                return PyStr.from_str("<element repr() failed>", self.ctx)

        args = varargs._.as_slice()
        if len(args) == 0:
            return []
        elif len(args) == 1:
            arg = args[0]
            if str_single:
                try:
                    return [arg.str(self)]
                except PyImplBase as _:
                    return [PyStr.from_str("<element str() failed>", self.ctx)]
            else:
                return [get_repr(arg)]
        else:
            return [get_repr(a) for a in args]


R = TypeVar("R")

PyResult: TypeAlias = "PyObjectRef"


@dataclass
class ExceptionStack:
    exc: Optional[PyBaseExceptionRef]
    prev: Optional[ExceptionStack]


@dataclass
class PyGlobalState:
    settings: PySettings
    module_inits: stdlib.StdlibMap
    frozen: dict[str, FrozenModule]
    stack_size: int
    thread_count: int
    hash_secret: HashSecret
    atexit_funcs: list[tuple[PyObjectRef, FuncArgs]]
    codec_registry: CodecsRegistry


class InitParameter(enum.Enum):
    Internal = enum.auto()
    External = enum.auto()


@dataclass
class PySettings:
    debig: bool = False
    inspect: bool = False
    interactive: bool = False
    optimize: int = 0
    no_user_site: bool = False
    no_site: bool = False
    ignore_environment: bool = False
    verbose: int = 0
    quiet: bool = False
    dont_write_bytecode: bool = False
    bytes_warning: int = 0
    xopts: list[tuple[str, Optional[str]]] = field(default_factory=list)
    isolated: bool = False
    dev_mode: bool = False
    warnopts: list[str] = field(default_factory=list)
    path_list: list[str] = field(default_factory=list)  # FIXME
    argv: list[str] = field(default_factory=list)
    hash_seed: Optional[int] = None
    stdio_unbuffered: bool = False


class TraceEvent(enum.Enum):
    Call = enum.auto()
    Return = enum.auto()


@dataclass
class Interpreter:
    vm: VirtualMachine

    @staticmethod
    def new(settings: PySettings, init: InitParameter) -> Interpreter:
        return Interpreter.new_with_init(settings, lambda _: init)

    @staticmethod
    def new_with_init(
        settings: PySettings, init: Callable[[VirtualMachine], InitParameter]
    ) -> Interpreter:
        vm = VirtualMachine.new(settings)
        vm.initialize(init(vm))
        return Interpreter(vm)

    def enter(self, f: Callable[[VirtualMachine], R]) -> R:
        return enter_vm(self.vm, lambda: f(self.vm))

    @staticmethod
    def default() -> Interpreter:
        return Interpreter.new(PySettings(), InitParameter.External)


def enter_vm(vm: VirtualMachine, f: Callable[[], R]) -> R:
    # TODO!!!!
    # raise NotImplementedError
    return f()
