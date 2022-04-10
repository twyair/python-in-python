from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, TypeAlias
from common.error import PyImplError
from vm.pyobject import PyContext

if TYPE_CHECKING:
    from vm.builtins.pytype import PyType, PyTypeRef
    from vm.pyobjectrc import PyObjectRef, PyRef
    from vm.builtins.tuple import PyTupleRef
    from vm.builtins.traceback import PyTracebackRef
    from vm.vm import VirtualMachine
import vm.pyobject as po
import vm.builtins.tuple as pytuple


@po.pyimpl()  # TODO
@po.pyclass("BaseException")
@dataclass
class PyBaseException(po.PyClassImpl, po.PyValueMixin):
    traceback: Optional[PyTracebackRef]
    cause: Optional[PyRef[PyBaseException]]
    context: Optional[PyRef[PyBaseException]]
    suppress_context: bool
    args: PyTupleRef

    def into_ref(self: PyBaseException, vm: VirtualMachine) -> PyBaseExceptionRef:
        return PyRef.new_ref(self, self.class_(vm), None)

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.exceptions.base_exception_type

    @classmethod
    def try_from_object(cls, vm: VirtualMachine, obj: PyObjectRef) -> PyBaseException:
        class_ = cls.class_(vm)
        if obj.isinstance(class_):
            return obj.downcast(cls).payload
            # TODO: .map_err(|obj| pyref_payload_error(vm, class, obj))
        else:
            return cls.special_retrieve(vm, obj)  # FIXME!
            # TODO: .unwrap_or_else(|| Err(pyref_type_error(vm, class, obj)))

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


PyBaseExceptionRef: TypeAlias = "PyRef[PyBaseException]"


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

        # FIXME!

        system_exit = base_exception_type  # PySystemExit.init_bare_type()
        keyboard_interrupt = base_exception_type  # PyKeyboardInterrupt.init_bare_type()
        generator_exit = base_exception_type  # PyGeneratorExit.init_bare_type()

        exception_type = base_exception_type  # PyException.init_bare_type()
        stop_iteration = base_exception_type  # PyStopIteration.init_bare_type()
        stop_async_iteration = (
            base_exception_type  # PyStopAsyncIteration.init_bare_type()
        )
        arithmetic_error = base_exception_type  # PyArithmeticError.init_bare_type()
        floating_point_error = (
            base_exception_type  # PyFloatingPointError.init_bare_type()
        )
        overflow_error = base_exception_type  # PyOverflowError.init_bare_type()
        zero_division_error = (
            base_exception_type  # PyZeroDivisionError.init_bare_type()
        )

        assertion_error = base_exception_type  # PyAssertionError.init_bare_type()
        attribute_error = base_exception_type  # PyAttributeError.init_bare_type()
        buffer_error = base_exception_type  # PyBufferError.init_bare_type()
        eof_error = base_exception_type  # PyEOFError.init_bare_type()

        import_error = base_exception_type  # PyImportError.init_bare_type()
        module_not_found_error = (
            base_exception_type  # PyModuleNotFoundError.init_bare_type()
        )

        lookup_error = base_exception_type  # PyLookupError.init_bare_type()
        index_error = base_exception_type  # PyIndexError.init_bare_type()
        key_error = base_exception_type  # PyKeyError.init_bare_type()

        memory_error = base_exception_type  # PyMemoryError.init_bare_type()

        name_error = base_exception_type  # PyNameError.init_bare_type()
        unbound_local_error = (
            base_exception_type  # PyUnboundLocalError.init_bare_type()
        )

        # // os errors
        os_error = base_exception_type  # PyOSError.init_bare_type()
        blocking_io_error = base_exception_type  # PyBlockingIOError.init_bare_type()
        child_process_error = (
            base_exception_type  # PyChildProcessError.init_bare_type()
        )

        connection_error = base_exception_type  # PyConnectionError.init_bare_type()
        broken_pipe_error = base_exception_type  # PyBrokenPipeError.init_bare_type()
        connection_aborted_error = (
            base_exception_type  # PyConnectionAbortedError.init_bare_type()
        )
        connection_refused_error = (
            base_exception_type  # PyConnectionRefusedError.init_bare_type()
        )
        connection_reset_error = (
            base_exception_type  # PyConnectionResetError.init_bare_type()
        )

        file_exists_error = base_exception_type  # PyFileExistsError.init_bare_type()
        file_not_found_error = (
            base_exception_type  # PyFileNotFoundError.init_bare_type()
        )
        interrupted_error = base_exception_type  # PyInterruptedError.init_bare_type()
        is_a_directory_error = (
            base_exception_type  # PyIsADirectoryError.init_bare_type()
        )
        not_a_directory_error = (
            base_exception_type  # PyNotADirectoryError.init_bare_type()
        )
        permission_error = base_exception_type  # PyPermissionError.init_bare_type()
        process_lookup_error = (
            base_exception_type  # PyProcessLookupError.init_bare_type()
        )
        timeout_error = base_exception_type  # PyTimeoutError.init_bare_type()

        reference_error = base_exception_type  # PyReferenceError.init_bare_type()

        runtime_error = base_exception_type  # PyRuntimeError.init_bare_type()
        not_implemented_error = (
            base_exception_type  # PyNotImplementedError.init_bare_type()
        )
        recursion_error = base_exception_type  # PyRecursionError.init_bare_type()

        syntax_error = base_exception_type  # PySyntaxError.init_bare_type()
        indentation_error = base_exception_type  # PyIndentationError.init_bare_type()
        tab_error = base_exception_type  # PyTabError.init_bare_type()

        system_error = base_exception_type  # PySystemError.init_bare_type()
        type_error = base_exception_type  # PyTypeError.init_bare_type()
        value_error = base_exception_type  # PyValueError.init_bare_type()
        unicode_error = base_exception_type  # PyUnicodeError.init_bare_type()
        unicode_decode_error = (
            base_exception_type  # PyUnicodeDecodeError.init_bare_type()
        )
        unicode_encode_error = (
            base_exception_type  # PyUnicodeEncodeError.init_bare_type()
        )
        unicode_translate_error = (
            base_exception_type  # PyUnicodeTranslateError.init_bare_type()
        )

        # #[cfg(feature = base_exception_type# "jit")]
        # jit_error = base_exception_type# PyJitError.init_bare_type()

        warning = base_exception_type  # PyWarning.init_bare_type()
        deprecation_warning = (
            base_exception_type  # PyDeprecationWarning.init_bare_type()
        )
        pending_deprecation_warning = (
            base_exception_type  # PyPendingDeprecationWarning.init_bare_type()
        )
        runtime_warning = base_exception_type  # PyRuntimeWarning.init_bare_type()
        syntax_warning = base_exception_type  # PySyntaxWarning.init_bare_type()
        user_warning = base_exception_type  # PyUserWarning.init_bare_type()
        future_warning = base_exception_type  # PyFutureWarning.init_bare_type()
        import_warning = base_exception_type  # PyImportWarning.init_bare_type()
        unicode_warning = base_exception_type  # PyUnicodeWarning.init_bare_type()
        bytes_warning = base_exception_type  # PyBytesWarning.init_bare_type()
        resource_warning = base_exception_type  # PyResourceWarning.init_bare_type()
        encoding_warning = base_exception_type  # PyEncodingWarning.init_bare_type()

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
        # FIXME!!!!

        return


@dataclass
class ExceptionCtor(ABC):
    @staticmethod
    def try_from_object(vm: VirtualMachine, obj: PyObjectRef) -> ExceptionCtor:
        try:
            cls = obj.downcast(PyType)
        except PyImplError as err:
            pass
        else:
            if cls.payload.issubclass(vm.ctx.exceptions.base_exception_type):
                return ExceptionCtorClass(cls)
        try:
            base = obj.downcast(PyBaseException)
        except PyImplError as err:
            vm.new_type_error(
                f"exceptions must be classes or instances deriving from BaseException, not {err.obj.class_().payload.name()}"
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
