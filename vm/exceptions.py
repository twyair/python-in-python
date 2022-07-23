from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Optional, TypeAlias
from common.deco import pymethod
from common.error import PyImplError
from vm.builtins.pystr import PyStrRef
from vm.function_ import FuncArgs
from vm.pyobject import PyContext

if TYPE_CHECKING:
    from vm.builtins.pytype import PyTypeRef
    from vm.pyobjectrc import PyObjectRef, PyRef
    from vm.builtins.tuple import PyTupleRef
    from vm.builtins.traceback import PyTracebackRef
    from vm.vm import VirtualMachine

import vm.pyobject as po
import vm.builtins.tuple as pytuple
import vm.builtins.pytype as pytype


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyclass("BaseException")
@dataclass
class PyBaseException(po.PyClassImpl):
    traceback: Optional[PyTracebackRef]
    cause: Optional[PyRef[PyBaseException]]
    context: Optional[PyRef[PyBaseException]]
    suppress_context: bool
    args: PyTupleRef

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.base_exception_type

    @staticmethod
    def new(args: list[PyObjectRef], vm: VirtualMachine) -> PyBaseException:
        return PyBaseException(
            traceback=None,
            cause=None,
            context=None,
            suppress_context=False,
            args=pytuple.PyTuple.new_ref(args, vm.ctx),
        )

    def set_cause(self, cause: Optional[PyBaseExceptionRef]) -> None:
        self.cause = cause

    def get_arg(self, idx: int) -> PyObjectRef:
        return self.args._.as_slice()[idx]

    def as_str(self, vm: VirtualMachine) -> PyStrRef:
        str_args = vm.exception_args_as_string(self.args, True)
        if not str_args:
            return vm.ctx.new_str("")
        elif len(str_args) == 1:
            return str_args[0]
        else:
            return vm.ctx.new_str(
                "({})".format(", ".join(s._.as_str() for s in str_args))
            )

    @pymethod(True)
    def i__str__(self, vm: VirtualMachine) -> PyObjectRef:
        return self.as_str(vm)


PyBaseExceptionRef: TypeAlias = "PyRef[PyBaseException]"


def none_getter(vm: VirtualMachine, obj: PyObjectRef) -> PyObjectRef:
    return vm.ctx.get_none()


def make_arg_getter(
    idx: int,
) -> Callable[[VirtualMachine, PyBaseExceptionRef], PyObjectRef]:
    return lambda vm, exc: exc._.get_arg(idx)


def key_error_str(vm: VirtualMachine, args: FuncArgs) -> PyStrRef:
    exc = args.take_positional_arg().downcast(PyBaseException)
    args_ = exc._.args
    if args_._.len() == 1:
        return vm.exception_args_as_string(args_, False)[0]
    else:
        return exc._.as_str(vm)


def system_exit_code(vm: VirtualMachine, exc: PyBaseExceptionRef) -> PyObjectRef:
    l = exc._.args._.as_slice()
    if not l:
        return vm.ctx.get_none()
    code = l[0]
    raise NotImplementedError


def extend_exception(
    exc_struct, ctx: PyContext, class_: PyTypeRef, d: Optional[dict[str, Any]] = None
) -> None:
    exc_struct.extend_class(ctx, class_)
    if d is not None:
        for name, value in d.items():
            class_._.set_str_attr(name, value)


@dataclass
class ExceptionZoo:
    base_exception_type: PyTypeRef
    system_exit: PyTypeRef
    keyboard_interrupt: PyTypeRef
    generator_exit: PyTypeRef
    exception_type: PyTypeRef
    stop_iteration: PyTypeRef
    stop_async_iteration: PyTypeRef
    arithmetic_error: PyTypeRef
    floating_point_error: PyTypeRef
    overflow_error: PyTypeRef
    zero_division_error: PyTypeRef
    assertion_error: PyTypeRef
    attribute_error: PyTypeRef
    buffer_error: PyTypeRef
    eof_error: PyTypeRef
    import_error: PyTypeRef
    module_not_found_error: PyTypeRef
    lookup_error: PyTypeRef
    index_error: PyTypeRef
    key_error: PyTypeRef
    memory_error: PyTypeRef
    name_error: PyTypeRef
    unbound_local_error: PyTypeRef
    os_error: PyTypeRef
    blocking_io_error: PyTypeRef
    child_process_error: PyTypeRef
    connection_error: PyTypeRef
    broken_pipe_error: PyTypeRef
    connection_aborted_error: PyTypeRef
    connection_refused_error: PyTypeRef
    connection_reset_error: PyTypeRef
    file_exists_error: PyTypeRef
    file_not_found_error: PyTypeRef
    interrupted_error: PyTypeRef
    is_a_directory_error: PyTypeRef
    not_a_directory_error: PyTypeRef
    permission_error: PyTypeRef
    process_lookup_error: PyTypeRef
    timeout_error: PyTypeRef
    reference_error: PyTypeRef
    runtime_error: PyTypeRef
    not_implemented_error: PyTypeRef
    recursion_error: PyTypeRef
    syntax_error: PyTypeRef
    indentation_error: PyTypeRef
    tab_error: PyTypeRef
    system_error: PyTypeRef
    type_error: PyTypeRef
    value_error: PyTypeRef
    unicode_error: PyTypeRef
    unicode_decode_error: PyTypeRef
    unicode_encode_error: PyTypeRef
    unicode_translate_error: PyTypeRef

    warning: PyTypeRef
    deprecation_warning: PyTypeRef
    pending_deprecation_warning: PyTypeRef
    runtime_warning: PyTypeRef
    syntax_warning: PyTypeRef
    user_warning: PyTypeRef
    future_warning: PyTypeRef
    import_warning: PyTypeRef
    unicode_warning: PyTypeRef
    bytes_warning: PyTypeRef
    resource_warning: PyTypeRef
    encoding_warning: PyTypeRef

    @staticmethod
    def init() -> ExceptionZoo:
        base_exception_type = PyBaseException.init_bare_type()

        system_exit = PySystemExit.init_bare_type()
        keyboard_interrupt = PyKeyboardInterrupt.init_bare_type()
        generator_exit = PyGeneratorExit.init_bare_type()

        exception_type = PyException.init_bare_type()
        stop_iteration = PyStopIteration.init_bare_type()
        stop_async_iteration = PyStopAsyncIteration.init_bare_type()
        arithmetic_error = PyArithmeticError.init_bare_type()
        floating_point_error = PyFloatingPointError.init_bare_type()
        overflow_error = PyOverflowError.init_bare_type()
        zero_division_error = PyZeroDivisionError.init_bare_type()

        assertion_error = PyAssertionError.init_bare_type()
        attribute_error = PyAttributeError.init_bare_type()
        buffer_error = PyBufferError.init_bare_type()
        eof_error = PyEOFError.init_bare_type()

        import_error = PyImportError.init_bare_type()
        module_not_found_error = PyModuleNotFoundError.init_bare_type()

        lookup_error = PyLookupError.init_bare_type()
        index_error = PyIndexError.init_bare_type()
        key_error = PyKeyError.init_bare_type()

        memory_error = PyMemoryError.init_bare_type()

        name_error = PyNameError.init_bare_type()
        unbound_local_error = PyUnboundLocalError.init_bare_type()

        # // os errors
        os_error = PyOSError.init_bare_type()
        blocking_io_error = PyBlockingIOError.init_bare_type()
        child_process_error = PyChildProcessError.init_bare_type()

        connection_error = PyConnectionError.init_bare_type()
        broken_pipe_error = PyBrokenPipeError.init_bare_type()
        connection_aborted_error = PyConnectionAbortedError.init_bare_type()
        connection_refused_error = PyConnectionRefusedError.init_bare_type()
        connection_reset_error = PyConnectionResetError.init_bare_type()

        file_exists_error = PyFileExistsError.init_bare_type()
        file_not_found_error = PyFileNotFoundError.init_bare_type()
        interrupted_error = PyInterruptedError.init_bare_type()
        is_a_directory_error = PyIsADirectoryError.init_bare_type()
        not_a_directory_error = PyNotADirectoryError.init_bare_type()
        permission_error = PyPermissionError.init_bare_type()
        process_lookup_error = PyProcessLookupError.init_bare_type()
        timeout_error = PyTimeoutError.init_bare_type()

        reference_error = PyReferenceError.init_bare_type()

        runtime_error = PyRuntimeError.init_bare_type()
        not_implemented_error = PyNotImplementedError.init_bare_type()
        recursion_error = PyRecursionError.init_bare_type()

        syntax_error = PySyntaxError.init_bare_type()
        indentation_error = PyIndentationError.init_bare_type()
        tab_error = PyTabError.init_bare_type()

        system_error = PySystemError.init_bare_type()
        type_error = PyTypeError.init_bare_type()
        value_error = PyValueError.init_bare_type()
        unicode_error = PyUnicodeError.init_bare_type()
        unicode_decode_error = PyUnicodeDecodeError.init_bare_type()
        unicode_encode_error = PyUnicodeEncodeError.init_bare_type()
        unicode_translate_error = PyUnicodeTranslateError.init_bare_type()

        # #[cfg(feature = base_exception_type# "jit")]
        # jit_error = base_exception_type# PyJitError.init_bare_type()

        warning = PyWarning.init_bare_type()
        deprecation_warning = PyDeprecationWarning.init_bare_type()
        pending_deprecation_warning = PyPendingDeprecationWarning.init_bare_type()
        runtime_warning = PyRuntimeWarning.init_bare_type()
        syntax_warning = PySyntaxWarning.init_bare_type()
        user_warning = PyUserWarning.init_bare_type()
        future_warning = PyFutureWarning.init_bare_type()
        import_warning = PyImportWarning.init_bare_type()
        unicode_warning = PyUnicodeWarning.init_bare_type()
        bytes_warning = PyBytesWarning.init_bare_type()
        resource_warning = PyResourceWarning.init_bare_type()
        encoding_warning = PyEncodingWarning.init_bare_type()

        return ExceptionZoo(
            base_exception_type=base_exception_type,
            system_exit=system_exit,
            keyboard_interrupt=keyboard_interrupt,
            generator_exit=generator_exit,
            exception_type=exception_type,
            stop_iteration=stop_iteration,
            stop_async_iteration=stop_async_iteration,
            arithmetic_error=arithmetic_error,
            floating_point_error=floating_point_error,
            overflow_error=overflow_error,
            zero_division_error=zero_division_error,
            assertion_error=assertion_error,
            attribute_error=attribute_error,
            buffer_error=buffer_error,
            eof_error=eof_error,
            import_error=import_error,
            module_not_found_error=module_not_found_error,
            lookup_error=lookup_error,
            index_error=index_error,
            key_error=key_error,
            memory_error=memory_error,
            name_error=name_error,
            unbound_local_error=unbound_local_error,
            os_error=os_error,
            blocking_io_error=blocking_io_error,
            child_process_error=child_process_error,
            connection_error=connection_error,
            broken_pipe_error=broken_pipe_error,
            connection_aborted_error=connection_aborted_error,
            connection_refused_error=connection_refused_error,
            connection_reset_error=connection_reset_error,
            file_exists_error=file_exists_error,
            file_not_found_error=file_not_found_error,
            interrupted_error=interrupted_error,
            is_a_directory_error=is_a_directory_error,
            not_a_directory_error=not_a_directory_error,
            permission_error=permission_error,
            process_lookup_error=process_lookup_error,
            timeout_error=timeout_error,
            reference_error=reference_error,
            runtime_error=runtime_error,
            not_implemented_error=not_implemented_error,
            recursion_error=recursion_error,
            syntax_error=syntax_error,
            indentation_error=indentation_error,
            tab_error=tab_error,
            system_error=system_error,
            type_error=type_error,
            value_error=value_error,
            unicode_error=unicode_error,
            unicode_decode_error=unicode_decode_error,
            unicode_encode_error=unicode_encode_error,
            unicode_translate_error=unicode_translate_error,
            # #[cfg(feature = "jit")]
            # jit_error,
            warning=warning,
            deprecation_warning=deprecation_warning,
            pending_deprecation_warning=pending_deprecation_warning,
            runtime_warning=runtime_warning,
            syntax_warning=syntax_warning,
            user_warning=user_warning,
            future_warning=future_warning,
            import_warning=import_warning,
            unicode_warning=unicode_warning,
            bytes_warning=bytes_warning,
            resource_warning=resource_warning,
            encoding_warning=encoding_warning,
        )

    @staticmethod
    def extend(ctx: PyContext) -> None:
        excs = ctx.exceptions
        PyBaseException.extend_class(ctx, excs.base_exception_type)

        extend_exception(
            PySystemExit,
            ctx,
            excs.system_exit,
            {
                "code": ctx.new_readonly_getset(
                    "code", excs.system_exit, system_exit_code
                )
            },
        )
        extend_exception(PyKeyboardInterrupt, ctx, excs.keyboard_interrupt)
        extend_exception(PyGeneratorExit, ctx, excs.generator_exit)

        extend_exception(PyException, ctx, excs.exception_type)

        extend_exception(
            PyStopIteration,
            ctx,
            excs.stop_iteration,
            {
                "value": ctx.new_readonly_getset(
                    "value", excs.stop_iteration.clone(), make_arg_getter(0)
                ),
            },
        )
        extend_exception(PyStopAsyncIteration, ctx, excs.stop_async_iteration)

        extend_exception(PyArithmeticError, ctx, excs.arithmetic_error)
        extend_exception(PyFloatingPointError, ctx, excs.floating_point_error)
        extend_exception(PyOverflowError, ctx, excs.overflow_error)
        extend_exception(PyZeroDivisionError, ctx, excs.zero_division_error)

        extend_exception(PyAssertionError, ctx, excs.assertion_error)
        extend_exception(
            PyAttributeError,
            ctx,
            excs.attribute_error,
            {
                "name": ctx.get_none(),
                "obj": ctx.get_none(),
            },
        )
        extend_exception(PyBufferError, ctx, excs.buffer_error)
        extend_exception(PyEOFError, ctx, excs.eof_error)

        extend_exception(
            PyImportError,
            ctx,
            excs.import_error,
            {
                "msg": ctx.new_readonly_getset(
                    "msg", excs.import_error.clone(), make_arg_getter(0)
                ),
            },
        )
        extend_exception(PyModuleNotFoundError, ctx, excs.module_not_found_error)

        extend_exception(PyLookupError, ctx, excs.lookup_error)
        extend_exception(PyIndexError, ctx, excs.index_error)
        extend_exception(
            PyKeyError,
            ctx,
            excs.key_error,
            {
                "__str__": ctx.new_method(
                    ctx.new_str("__str__")._,
                    excs.key_error.clone(),
                    key_error_str,
                ),
            },
        )

        extend_exception(PyMemoryError, ctx, excs.memory_error)
        extend_exception(
            PyNameError,
            ctx,
            excs.name_error,
            {
                "name": ctx.get_none(),
            },
        )
        extend_exception(PyUnboundLocalError, ctx, excs.unbound_local_error)

        # FIXME:
        # // os errors:
        # let errno_getter =
        #     ctx.new_readonly_getset("errno", excs.os_error.clone(), |exc: PyBaseExceptionRef| {
        #         let args = exc.args()
        #         let args = args.as_slice()
        #         args.get(0).filter(|_| args.len() > 1).cloned()
        #     })
        # extend_exception(PyOSError, ctx, excs.os_error, {
        #     // POSIX exception code
        #     "errno": errno_getter.clone(),
        #     // exception strerror
        #     "strerror": ctx.new_readonly_getset("strerror", excs.os_error.clone(), make_arg_getter(1)),
        #     // exception filename
        #     "filename": ctx.none(),
        #     // second exception filename
        #     "filename2": ctx.none(),
        #     "__str__": ctx.new_method("__str__", excs.os_error.clone(), os_error_str),
        # })
        # // TODO: this isn't really accurate
        # #[cfg(windows)]
        # excs.os_error.set_str_attr("winerror", errno_getter.clone())

        extend_exception(PyBlockingIOError, ctx, excs.blocking_io_error)
        extend_exception(PyChildProcessError, ctx, excs.child_process_error)

        extend_exception(PyConnectionError, ctx, excs.connection_error)
        extend_exception(PyBrokenPipeError, ctx, excs.broken_pipe_error)
        extend_exception(PyConnectionAbortedError, ctx, excs.connection_aborted_error)
        extend_exception(PyConnectionRefusedError, ctx, excs.connection_refused_error)
        extend_exception(PyConnectionResetError, ctx, excs.connection_reset_error)

        extend_exception(PyFileExistsError, ctx, excs.file_exists_error)
        extend_exception(PyFileNotFoundError, ctx, excs.file_not_found_error)
        extend_exception(PyInterruptedError, ctx, excs.interrupted_error)
        extend_exception(PyIsADirectoryError, ctx, excs.is_a_directory_error)
        extend_exception(PyNotADirectoryError, ctx, excs.not_a_directory_error)
        extend_exception(PyPermissionError, ctx, excs.permission_error)
        extend_exception(PyProcessLookupError, ctx, excs.process_lookup_error)
        extend_exception(PyTimeoutError, ctx, excs.timeout_error)

        extend_exception(PyReferenceError, ctx, excs.reference_error)
        extend_exception(PyRuntimeError, ctx, excs.runtime_error)
        extend_exception(PyNotImplementedError, ctx, excs.not_implemented_error)
        extend_exception(PyRecursionError, ctx, excs.recursion_error)

        extend_exception(
            PySyntaxError,
            ctx,
            excs.syntax_error,
            {
                "msg": ctx.new_readonly_getset(
                    "msg", excs.syntax_error.clone(), make_arg_getter(0)
                ),
                # // TODO: members
                "filename": ctx.get_none(),
                "lineno": ctx.get_none(),
                "offset": ctx.get_none(),
                "text": ctx.get_none(),
            },
        )
        extend_exception(PyIndentationError, ctx, excs.indentation_error)
        extend_exception(PyTabError, ctx, excs.tab_error)

        extend_exception(PySystemError, ctx, excs.system_error)
        extend_exception(PyTypeError, ctx, excs.type_error)
        extend_exception(PyValueError, ctx, excs.value_error)
        extend_exception(PyUnicodeError, ctx, excs.unicode_error)
        extend_exception(
            PyUnicodeDecodeError,
            ctx,
            excs.unicode_decode_error,
            {
                "encoding": ctx.new_readonly_getset(
                    "encoding", excs.unicode_decode_error.clone(), make_arg_getter(0)
                ),
                "object": ctx.new_readonly_getset(
                    "object", excs.unicode_decode_error.clone(), make_arg_getter(1)
                ),
                "start": ctx.new_readonly_getset(
                    "start", excs.unicode_decode_error.clone(), make_arg_getter(2)
                ),
                "end": ctx.new_readonly_getset(
                    "end", excs.unicode_decode_error.clone(), make_arg_getter(3)
                ),
                "reason": ctx.new_readonly_getset(
                    "reason", excs.unicode_decode_error.clone(), make_arg_getter(4)
                ),
            },
        )
        extend_exception(
            PyUnicodeEncodeError,
            ctx,
            excs.unicode_encode_error,
            {
                "encoding": ctx.new_readonly_getset(
                    "encoding", excs.unicode_encode_error.clone(), make_arg_getter(0)
                ),
                "object": ctx.new_readonly_getset(
                    "object", excs.unicode_encode_error.clone(), make_arg_getter(1)
                ),
                "start": ctx.new_readonly_getset(
                    "start",
                    excs.unicode_encode_error.clone(),
                    make_arg_getter(2),
                ),
                "end": ctx.new_readonly_getset(
                    "end", excs.unicode_encode_error.clone(), make_arg_getter(3)
                ),
                "reason": ctx.new_readonly_getset(
                    "reason", excs.unicode_encode_error.clone(), make_arg_getter(4)
                ),
            },
        )
        extend_exception(
            PyUnicodeTranslateError,
            ctx,
            excs.unicode_translate_error,
            {
                "encoding": ctx.new_readonly_getset(
                    "encoding", excs.unicode_translate_error.clone(), none_getter
                ),
                "object": ctx.new_readonly_getset(
                    "object", excs.unicode_translate_error.clone(), make_arg_getter(0)
                ),
                "start": ctx.new_readonly_getset(
                    "start", excs.unicode_translate_error.clone(), make_arg_getter(1)
                ),
                "end": ctx.new_readonly_getset(
                    "end", excs.unicode_translate_error.clone(), make_arg_getter(2)
                ),
                "reason": ctx.new_readonly_getset(
                    "reason", excs.unicode_translate_error.clone(), make_arg_getter(3)
                ),
            },
        )

        # #[cfg(feature = "jit")]
        # extend_exception(PyJitError, ctx, excs.jit_error)

        extend_exception(PyWarning, ctx, excs.warning)
        extend_exception(PyDeprecationWarning, ctx, excs.deprecation_warning)
        extend_exception(
            PyPendingDeprecationWarning, ctx, excs.pending_deprecation_warning
        )
        extend_exception(PyRuntimeWarning, ctx, excs.runtime_warning)
        extend_exception(PySyntaxWarning, ctx, excs.syntax_warning)
        extend_exception(PyUserWarning, ctx, excs.user_warning)
        extend_exception(PyFutureWarning, ctx, excs.future_warning)
        extend_exception(PyImportWarning, ctx, excs.import_warning)
        extend_exception(PyUnicodeWarning, ctx, excs.unicode_warning)
        extend_exception(PyBytesWarning, ctx, excs.bytes_warning)
        extend_exception(PyResourceWarning, ctx, excs.resource_warning)
        extend_exception(PyEncodingWarning, ctx, excs.encoding_warning)


@dataclass
class ExceptionCtor(ABC):
    @staticmethod
    def try_from_object(vm: VirtualMachine, obj: PyObjectRef) -> ExceptionCtor:
        try:
            cls = obj.downcast(pytype.PyType)
        except PyImplError as err:
            pass
        else:
            if cls._.issubclass(vm.ctx.exceptions.base_exception_type):
                return ExceptionCtorClass(cls)
        try:
            base = obj.downcast(PyBaseException)
        except PyImplError as err:
            vm.new_type_error(
                f"exceptions must be classes or instances deriving from BaseException, not {err.obj.class_()._.name()}"
            )
        else:
            return ExceptionCtorInstance(base)

    @abstractmethod
    def instantiate(self, vm: VirtualMachine) -> PyBaseExceptionRef:
        ...

    @abstractmethod
    def instantiate_value(
        self, value: PyObjectRef, vm: VirtualMachine
    ) -> PyBaseExceptionRef:
        ...


@dataclass
class ExceptionCtorClass(ExceptionCtor):
    value: PyTypeRef

    def instantiate(self, vm: VirtualMachine) -> PyBaseExceptionRef:
        return vm.invoke_exception(self.value, [])

    def instantiate_value(
        self, value: PyObjectRef, vm: VirtualMachine
    ) -> PyBaseExceptionRef:
        exc_inst = value.downcast(PyBaseException)
        if exc_inst is not None and exc_inst.isinstance(self.value):
            return exc_inst
        else:
            args = []
            raise NotImplementedError
            vm.invoke_exception(self.value, args)


@dataclass
class ExceptionCtorInstance(ExceptionCtor):
    value: PyBaseExceptionRef

    def instantiate(self, vm: VirtualMachine) -> PyBaseExceptionRef:
        return self.value

    def instantiate_value(
        self, value: PyObjectRef, vm: VirtualMachine
    ) -> PyBaseExceptionRef:
        exc_inst = value.downcast(PyBaseException)
        if exc_inst is not None:
            vm.new_type_error("instance exception may not have a separate value")
        else:
            return self.value


# @po.tp_flags(basetype=True, has_dict=True)
# @po.pyimpl()
# @po.pyexception("SystemExit", "PyBaseException", "Request to exit from the interpreter.")
# @dataclass
# class PySystemExit(po.PyClassImpl):
#     @classmethod
#     def class_(cls, vm: VirtualMachine) -> PyTypeRef:
#         return vm.ctx.exceptions.system_exit
@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception("SystemExit", PyBaseException, "Request to exit from the interpreter.")
@dataclass
class PySystemExit(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.system_exit


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception("GeneratorExit", PyBaseException, "Request that a generator exit.")
@dataclass
class PyGeneratorExit(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.generator_exit


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception("KeyboardInterrupt", PyBaseException, "Program interrupted by user.")
@dataclass
class PyKeyboardInterrupt(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.keyboard_interrupt


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception(
    "Exception", PyBaseException, "Common base class for all non-exit exceptions."
)
@dataclass
class PyException(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.exception_type


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception(
    "StopIteration", PyException, "Signal the end from iterator.__next__()."
)
@dataclass
class PyStopIteration(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.stop_iteration


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception(
    "StopAsyncIteration", PyException, "Signal the end from iterator.__anext__()."
)
@dataclass
class PyStopAsyncIteration(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.stop_async_iteration


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception("ArithmeticError", PyException, "Base class for arithmetic errors.")
@dataclass
class PyArithmeticError(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.arithmetic_error


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception(
    "FloatingPointError", PyArithmeticError, "Floating point operation failed."
)
@dataclass
class PyFloatingPointError(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.floating_point_error


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception(
    "OverflowError", PyArithmeticError, "Result too large to be represented."
)
@dataclass
class PyOverflowError(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.overflow_error


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception(
    "ZeroDivisionError",
    PyArithmeticError,
    "Second argument to a division or modulo operation was zero.",
)
@dataclass
class PyZeroDivisionError(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.zero_division_error


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception("AssertionError", PyException, "Assertion failed.")
@dataclass
class PyAssertionError(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.assertion_error


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception("AttributeError", PyException, "Attribute not found.")
@dataclass
class PyAttributeError(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.attribute_error


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception("BufferError", PyException, "Buffer error.")
@dataclass
class PyBufferError(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.buffer_error


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception("EOFError", PyException, "Read beyond end of file.")
@dataclass
class PyEOFError(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.eof_error


# TODO:
#     base_exception_new,
#     import_error_init,
@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception(
    "ImportError",
    PyException,
    "Import can't find module, or can't find name in module.",
)
@dataclass
class PyImportError(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.import_error


# fn base_exception_new(cls: PyTypeRef, args: FuncArgs, vm: &VirtualMachine) -> PyResult {
#     PyBaseException::slot_new(cls, args, vm)
# }

# fn import_error_init(
#     zelf: PyRef<PyBaseException>,
#     args: FuncArgs,
#     vm: &VirtualMachine,
# ) -> PyResult<()> {
#     let zelf: PyObjectRef = zelf.into();
#     zelf.set_attr(
#         "name",
#         vm.unwrap_or_none(args.kwargs.get("name").cloned()),
#         vm,
#     )?;
#     zelf.set_attr(
#         "path",
#         vm.unwrap_or_none(args.kwargs.get("path").cloned()),
#         vm,
#     )?;
#     Ok(())
# }


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception("ModuleNotFoundError", PyImportError, "Module not found.")
@dataclass
class PyModuleNotFoundError(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.module_not_found_error


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception("LookupError", PyException, "Base class for lookup errors.")
@dataclass
class PyLookupError(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.lookup_error


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception("IndexError", PyLookupError, "Sequence index out of range.")
@dataclass
class PyIndexError(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.index_error


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception("KeyError", PyLookupError, "Mapping key not found.")
@dataclass
class PyKeyError(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.key_error


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception("MemoryError", PyException, "Out of memory.")
@dataclass
class PyMemoryError(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.memory_error


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception("NameError", PyException, "Name not found globally.")
@dataclass
class PyNameError(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.name_error


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception(
    "UnboundLocalError",
    PyNameError,
    "Local name referenced but not bound to a value.",
)
@dataclass
class PyUnboundLocalError(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.unbound_local_error


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception("OSError", PyException, "Base class for I/O related errors.")
@dataclass
class PyOSError(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.os_error


# TODO:
# #[cfg(not(target_arch = "wasm32"))]
# fn os_error_optional_new(
#     args: Vec<PyObjectRef>,
#     vm: &VirtualMachine,
# ) -> Option<PyBaseExceptionRef> {
#     let len = args.len();
#     if len >= 2 {
#         let args = args.as_slice();
#         let errno = &args[0];
#         errno
#             .payload_if_subclass::<PyInt>(vm)
#             .and_then(|errno| errno.try_to_primitive::<i32>(vm).ok())
#             .and_then(|errno| super::raw_os_error_to_exc_type(errno, vm))
#             .and_then(|typ| vm.invoke_exception(typ, args.to_vec()).ok())
#     } else {
#         None
#     }
# }
# #[cfg(not(target_arch = "wasm32"))]
# fn os_error_new(cls: PyTypeRef, args: FuncArgs, vm: &VirtualMachine) -> PyResult {
#     // We need this method, because of how `CPython` copies `init`
#     // from `BaseException` in `SimpleExtendsException` macro.
#     // See: `BaseException_new`
#     if cls.name().deref() == vm.ctx.exceptions.os_error.name().deref() {
#         match os_error_optional_new(args.args.to_vec(), vm) {
#             Some(error) => error.into_pyresult(vm),
#             None => PyBaseException::slot_new(cls, args, vm),
#         }
#     } else {
#         PyBaseException::slot_new(cls, args, vm)
#     }
# }
# #[cfg(target_arch = "wasm32")]
# fn os_error_new(cls: PyTypeRef, args: FuncArgs, vm: &VirtualMachine) -> PyResult {
#     PyBaseException::slot_new(cls, args, vm)
# }

# fn base_exception_init(
#     zelf: PyRef<PyBaseException>,
#     args: FuncArgs,
#     vm: &VirtualMachine,
# ) -> PyResult<()> {
#     PyBaseException::init(zelf, args, vm)
# }


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception("BlockingIOError", PyOSError, "I/O operation would block.")
@dataclass
class PyBlockingIOError(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.blocking_io_error


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception("ChildProcessError", PyOSError, "Child process error.")
@dataclass
class PyChildProcessError(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.child_process_error


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception("ConnectionError", PyOSError, "Connection error.")
@dataclass
class PyConnectionError(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.connection_error


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception("BrokenPipeError", PyConnectionError, "Broken pipe.")
@dataclass
class PyBrokenPipeError(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.broken_pipe_error


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception("ConnectionAbortedError", PyConnectionError, "Connection aborted.")
@dataclass
class PyConnectionAbortedError(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.connection_aborted_error


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception("ConnectionRefusedError", PyConnectionError, "Connection refused.")
@dataclass
class PyConnectionRefusedError(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.connection_refused_error


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception("ConnectionResetError", PyConnectionError, "Connection reset.")
@dataclass
class PyConnectionResetError(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.connection_reset_error


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception("FileExistsError", PyOSError, "File already exists.")
@dataclass
class PyFileExistsError(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.file_exists_error


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception("FileNotFoundError", PyOSError, "File not found.")
@dataclass
class PyFileNotFoundError(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.file_not_found_error


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception("InterruptedError", PyOSError, "Interrupted by signal.")
@dataclass
class PyInterruptedError(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.interrupted_error


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception(
    "IsADirectoryError", PyOSError, "Operation doesn't work on directories."
)
@dataclass
class PyIsADirectoryError(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.is_a_directory_error


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception("NotADirectoryError", PyOSError, "Operation only works on directories.")
@dataclass
class PyNotADirectoryError(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.not_a_directory_error


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception("PermissionError", PyOSError, "Not enough permissions.")
@dataclass
class PyPermissionError(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.permission_error


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception("ProcessLookupError", PyOSError, "Process not found.")
@dataclass
class PyProcessLookupError(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.process_lookup_error


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception("TimeoutError", PyOSError, "Timeout expired.")
@dataclass
class PyTimeoutError(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.timeout_error


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception(
    "ReferenceError", PyException, "Weak ref proxy used after referent went away."
)
@dataclass
class PyReferenceError(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.reference_error


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception("RuntimeError", PyException, "Unspecified run-time error.")
@dataclass
class PyRuntimeError(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.runtime_error


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception(
    "NotImplementedError",
    PyRuntimeError,
    "Method or function hasn't been implemented yet.",
)
@dataclass
class PyNotImplementedError(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.not_implemented_error


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception("RecursionError", PyRuntimeError, "Recursion limit exceeded.")
@dataclass
class PyRecursionError(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.recursion_error


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception("SyntaxError", PyException, "Invalid syntax.")
@dataclass
class PySyntaxError(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.syntax_error


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception("IndentationError", PySyntaxError, "Improper indentation.")
@dataclass
class PyIndentationError(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.indentation_error


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception("TabError", PyIndentationError, "Improper mixture of spaces and tabs.")
@dataclass
class PyTabError(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.tab_error


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception(
    "SystemError",
    PyException,
    "Internal error in the Python interpreter.\n\nPlease report this to the Python maintainer, along with the traceback,\nthe Python version, and the hardware/OS platform and version.",
)
@dataclass
class PySystemError(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.system_error


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception("TypeError", PyException, "Inappropriate argument type.")
@dataclass
class PyTypeError(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.type_error


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception(
    "ValueError", PyException, "Inappropriate argument value (of correct type)."
)
@dataclass
class PyValueError(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.value_error


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception("UnicodeError", PyValueError, "Unicode related error.")
@dataclass
class PyUnicodeError(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.unicode_error


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception("UnicodeDecodeError", PyUnicodeError, "Unicode decoding error.")
@dataclass
class PyUnicodeDecodeError(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.unicode_decode_error


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception("UnicodeEncodeError", PyUnicodeError, "Unicode encoding error.")
@dataclass
class PyUnicodeEncodeError(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.unicode_encode_error


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception("UnicodeTranslateError", PyUnicodeError, "Unicode translation error.")
@dataclass
class PyUnicodeTranslateError(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.unicode_translate_error


# #[cfg(feature = "jit")]
# define_exception {
#     "PyJitError",
#     "PyException",
#     "jit_error",
#     "JIT error."
# }

# // Warnings
@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception("Warning", PyException, "Base class for warning categories.")
@dataclass
class PyWarning(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.warning


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception(
    "DeprecationWarning",
    PyWarning,
    "Base class for warnings about deprecated features.",
)
@dataclass
class PyDeprecationWarning(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.deprecation_warning


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception(
    "PendingDeprecationWarning",
    PyWarning,
    "Base class for warnings about features which will be deprecated\nin the future.",
)
@dataclass
class PyPendingDeprecationWarning(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.pending_deprecation_warning


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception(
    "RuntimeWarning",
    PyWarning,
    "Base class for warnings about dubious runtime behavior.",
)
@dataclass
class PyRuntimeWarning(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.runtime_warning


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception(
    "SyntaxWarning", PyWarning, "Base class for warnings about dubious syntax."
)
@dataclass
class PySyntaxWarning(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.syntax_warning


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception(
    "UserWarning", PyWarning, "Base class for warnings generated by user code."
)
@dataclass
class PyUserWarning(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.user_warning


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception(
    "FutureWarning",
    PyWarning,
    "Base class for warnings about constructs that will change semantically\nin the future.",
)
@dataclass
class PyFutureWarning(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.future_warning


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception(
    "ImportWarning",
    PyWarning,
    "Base class for warnings about probable mistakes in module imports.",
)
@dataclass
class PyImportWarning(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.import_warning


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception(
    "UnicodeWarning",
    PyWarning,
    "Base class for warnings about Unicode related problems, mostly\nrelated to conversion problems.",
)
@dataclass
class PyUnicodeWarning(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.unicode_warning


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception(
    "BytesWarning",
    PyWarning,
    "Base class for warnings about bytes and buffer related problems, mostly\nrelated to conversion from str or comparing to str.",
)
@dataclass
class PyBytesWarning(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.bytes_warning


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception(
    "ResourceWarning", PyWarning, "Base class for warnings about resource usage."
)
@dataclass
class PyResourceWarning(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.resource_warning


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl()
@po.pyexception(
    "EncodingWarning", PyWarning, "Base class for warnings about encodings."
)
@dataclass
class PyEncodingWarning(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.encoding_warning
