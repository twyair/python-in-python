from __future__ import annotations
from typing import TYPE_CHECKING, Optional
from common.error import PyImplBase
from common.hash import PyHash
from vm import extend_module
from vm.types.slot import PyComparisonOp


if TYPE_CHECKING:
    from vm.vm import VirtualMachine
    from vm.function_ import FuncArgs
    from vm.pyobjectrc import PyObjectRef

import vm.function_ as fn
import vm.pyobjectrc as prc
import vm.pyobject as po
import vm.builtins.pystr as pystr
import vm.builtins.int as pyint
import vm.builtins.list as pylist
import vm.builtins.dict as pydict
import vm.builtins.iter as pyiter
import vm.builtins.function as pyfunction_
import vm.builtins.enumerate as pyenumerate
import vm.protocol.iter as viter
import vm.stdlib.sys as std_sys
from common.deco import pyfunction, pymodule
import vm.function.arguments as arg


@pymodule
class builtins(po.PyModuleImpl):
    @pyfunction
    @staticmethod
    def abs(x: PyObjectRef, /, *, vm: VirtualMachine) -> PyObjectRef:
        return vm._abs(x)

    @pyfunction
    @staticmethod
    def all(iterable: arg.ArgIterable, /, *, vm: VirtualMachine) -> bool:
        for item in iterable.iter(vm):
            if not item.try_to_bool(vm):
                return False
        return True

    @pyfunction
    @staticmethod
    def any(iterable: arg.ArgIterable, /, *, vm: VirtualMachine) -> bool:
        for item in iterable.iter(vm):
            if item.try_to_bool(vm):
                return True
        return False

    @pyfunction
    @staticmethod
    def ascii(obj: PyObjectRef, /, *, vm: VirtualMachine) -> PyObjectRef:
        raise NotImplementedError

    @pyfunction
    @staticmethod
    def bin(obj: PyObjectRef, /, *, vm: VirtualMachine) -> PyObjectRef:
        raise NotImplementedError

    @pyfunction
    @staticmethod
    def callable(obj: PyObjectRef, /, *, vm: VirtualMachine) -> PyObjectRef:
        return vm.ctx.new_bool(vm.is_callable(obj))

    @pyfunction
    @staticmethod
    def chr(i: pyint.PyIntRef, /, *, vm: VirtualMachine) -> str:
        x = i._.as_int()
        if x not in range(0x110000):
            vm.new_value_error("chr() arg not in range(0x110000)")
        return chr(x)

    # TODO: compile()

    @pyfunction
    @staticmethod
    def delattr(
        obj: PyObjectRef, attr: pystr.PyStrRef, /, *, vm: VirtualMachine
    ) -> None:
        obj.del_attr(attr, vm)

    @pyfunction
    @staticmethod
    def dir(
        obj: Optional[PyObjectRef] = None, /, *, vm: VirtualMachine
    ) -> pylist.PyList:
        if obj is None or vm.is_none(obj):
            return vm.dir(None)
        else:
            return vm.dir(obj)

    @pyfunction
    @staticmethod
    def divmod(a: PyObjectRef, b: PyObjectRef, /, *, vm: VirtualMachine) -> PyObjectRef:
        return vm._divmod(a, b)

    # # TODO: impl eval(), exec()

    @pyfunction
    @staticmethod
    def format(
        value: PyObjectRef,
        format_spec: Optional[pystr.PyStrRef],
        /,
        *,
        vm: VirtualMachine,
    ) -> pystr.PyStrRef:
        if format_spec is None:
            format_spec = pystr.PyStr("").into_ref(vm)

        res = vm.call_method(value, "__format__", FuncArgs([format_spec])).downcast_ref(
            pystr.PyStr
        )
        if res is None:
            vm.new_type_error(
                f"__format__ must return a str, not {value.class_()._.name()}"
            )
        return res

    @pyfunction
    @staticmethod
    def getattr(
        obj: PyObjectRef,
        attr: pystr.PyStrRef,
        default: Optional[PyObjectRef] = None,
        /,
        *,
        vm: VirtualMachine,
    ) -> PyObjectRef:
        if default is not None:
            r = vm.get_attribute_opt(obj, attr)
            if r is None:
                return default
            return r
        else:
            return obj.get_attr(attr, vm)

    @pyfunction
    @staticmethod
    def globals(*, vm: VirtualMachine) -> pydict.PyDictRef:
        return vm.current_globals()

    @pyfunction
    @staticmethod
    def hasattr(
        obj: PyObjectRef, attr: pystr.PyStrRef, /, *, vm: VirtualMachine
    ) -> bool:
        return vm.get_attribute_opt(obj, attr) is not None

    @pyfunction
    @staticmethod
    def hash(obj: PyObjectRef, /, *, vm: VirtualMachine) -> PyHash:
        return obj.hash(vm)

    # TODO: help()

    @pyfunction
    @staticmethod
    def hex(number: pyint.PyIntRef, /, *, vm: VirtualMachine) -> str:
        return hex(number._.as_int())

    @pyfunction
    @staticmethod
    def id(obj: PyObjectRef, /, *, vm: VirtualMachine) -> int:
        return obj.get_id()

    @pyfunction
    @staticmethod
    def input(
        prompt: Optional[pystr.PyStrRef], /, *, vm: VirtualMachine
    ) -> PyObjectRef:
        raise NotImplementedError

    @pyfunction
    @staticmethod
    def isinstance(
        obj: PyObjectRef, typ: PyObjectRef, /, *, vm: VirtualMachine
    ) -> bool:
        return obj.is_instance(typ, vm)

    @pyfunction
    @staticmethod
    def issubclass(
        subclass: PyObjectRef, typ: PyObjectRef, /, *, vm: VirtualMachine
    ) -> bool:
        return subclass.is_subclass(typ, vm)

    @pyfunction
    @staticmethod
    def iter(
        iter_target: PyObjectRef,
        sentinel: Optional[PyObjectRef] = None,
        /,
        *,
        vm: VirtualMachine,
    ) -> PyObjectRef:
        if sentinel is not None:
            callable_ = arg.ArgCallable.try_from_object(vm, iter_target)
            return pyiter.PyCallableIterator.new(callable_, sentinel).into_ref(vm)
        else:
            return iter_target.get_iter(vm).into_pyobject(vm)

    @pyfunction
    @staticmethod
    def len(obj: PyObjectRef, /, *, vm: VirtualMachine) -> int:
        return obj.length(vm)

    @pyfunction
    @staticmethod
    def locals(*, vm: VirtualMachine) -> PyObjectRef:
        return vm.current_locals().map(
            lambda x: x.into_object()
        )  # TODO: impl ArgMapping.map()

    @staticmethod
    def _min_or_max(
        args: FuncArgs, vm: VirtualMachine, func_name: str, op: PyComparisonOp
    ) -> PyObjectRef:
        raise NotImplementedError

    @pyfunction(False)
    @staticmethod
    def max(args: FuncArgs, vm: VirtualMachine):
        return builtins._min_or_max(args, vm, "max()", PyComparisonOp.Gt)

    @pyfunction(False)
    @staticmethod
    def min(args: FuncArgs, vm: VirtualMachine):
        return builtins._min_or_max(args, vm, "min()", PyComparisonOp.Lt)

    @pyfunction
    @staticmethod
    def next(
        iterator: PyObjectRef,
        default_value: Optional[PyObjectRef] = None,
        /,
        *,
        vm: VirtualMachine,
    ) -> PyObjectRef:
        raise NotImplementedError

    @pyfunction
    @staticmethod
    def oct(number: pyint.PyIntRef, /, *, vm: VirtualMachine) -> str:
        return oct(number._.as_int())

    # TODO: ord()
    # TODO: pow()

    @pyfunction
    @staticmethod
    def exit(code: Optional[PyObjectRef], /, *, vm: VirtualMachine) -> PyObjectRef:
        if code is None:
            code = vm.ctx.new_int(0)
        vm.new_exception(vm.ctx.exceptions.system_exit, [code])

    # TODO: del
    @pyfunction
    @staticmethod
    def pdebug(arg: PyObjectRef, *, vm: VirtualMachine) -> None:
        print("DEBUG:", arg.debug_repr())

    # TODO:
    # @pyfunction
    # @staticmethod
    # def print(
    #     *args: PyObjectRef,
    #     sep: Optional[PyObjectRef] = None,
    #     end: Optional[PyObjectRef] = None,
    #     flush: Optional[PyObjectRef] = None,
    #     file: Optional[PyObjectRef] = None,
    #     vm: VirtualMachine,
    # ) -> None:
    #     if file is None or vm.is_none(file):
    #         file = std_sys.sys.get_stdout(vm)

    #     write = lambda obj: vm.call_method(file, "write", fn.FuncArgs([obj]))

    #     if sep is None or vm.is_none(sep):
    #         sep = pystr.PyStr.from_str(" ", vm.ctx)

    #     first = True
    #     for object in args:
    #         if first:
    #             first = False
    #         else:
    #             write(sep)

    #         write(object.str(vm))

    #     if end is None or vm.is_none(end):
    #         end = pystr.PyStr.from_str("\n", vm.ctx)

    #     write(end)

    #     if flush is not None and flush.try_to_bool(vm):
    #         vm.call_method(file, "flush", fn.FuncArgs())

    #     return None

    @pyfunction
    @staticmethod
    def repr(obj: PyObjectRef, /, *, vm: VirtualMachine) -> PyObjectRef:
        return obj.repr(vm)

    @pyfunction
    @staticmethod
    def reversed(obj: PyObjectRef, /, *, vm: VirtualMachine) -> PyObjectRef:
        if (method := vm.get_method(obj, "__reversed__")) is not None:
            return vm.invoke(method, FuncArgs())
        else:
            vm.get_method_or_type_error(
                obj, "__getitem__", lambda: "argument to reversed() must be a sequence"
            )
            obj_iterator = pyenumerate.PyReverseSequenceIterator.new(
                obj, obj.length(vm)
            )
            return obj_iterator.into_object(vm)

    # TODO: round
    @pyfunction
    @staticmethod
    def setattr(
        obj: PyObjectRef,
        attr: pystr.PyStrRef,
        value: PyObjectRef,
        /,
        *,
        vm: VirtualMachine,
    ) -> None:
        obj.set_attr(attr, value, vm)

    # TODO: slice

    # TODO:
    # @pyfunction
    # @staticmethod
    # def sorted(iterable: PyObjectRef, opts:)

    # TODO: sum

    @pyfunction(False)
    @staticmethod
    def i__import__(args: FuncArgs, *, vm: VirtualMachine) -> PyObjectRef:
        return vm.invoke(vm.import_func, args)

    @pyfunction
    @staticmethod
    def vars(
        obj: Optional[PyObjectRef] = None, /, *, vm: VirtualMachine
    ) -> PyObjectRef:
        if obj is not None:
            try:
                return obj.get_attr(vm.ctx.new_str("__dict__"), vm)
            except PyImplBase as _:
                vm.new_type_error("vars() argument must have __dict__ attribute")
        else:
            return vm.current_locals().into_object()

    # TODO:
    # @pyfunction
    # @staticmethod
    # def __build_class__(
    #     function: prc.PyRef[pyfunction_.PyFunction],
    #     qualified_name: pystr.PyStrRef,
    #     bases: PosArgs,
    #     kwargs: KwArgs,
    #     *,
    #     vm: VirtualMachine,
    # ) -> PyObjectRef:
    #     raise NotImplementedError


def make_module(vm: VirtualMachine, module: PyObjectRef) -> None:
    # protocol.VecBuffer.make_class(vm.ctx)

    builtins.extend_module(vm, module)

    debug_mode = vm.state.settings.optimize == 0
    extend_module(
        vm,
        module,
        {
            "__debug__": vm.ctx.new_bool(debug_mode),
            "bool": vm.ctx.types.bool_type.clone(),
            "bytearray": vm.ctx.types.bytearray_type.clone(),
            "bytes": vm.ctx.types.bytes_type.clone(),
            "classmethod": vm.ctx.types.classmethod_type.clone(),
            "complex": vm.ctx.types.complex_type.clone(),
            "dict": vm.ctx.types.dict_type.clone(),
            "enumerate": vm.ctx.types.enumerate_type.clone(),
            "float": vm.ctx.types.float_type.clone(),
            "frozenset": vm.ctx.types.frozenset_type.clone(),
            "filter": vm.ctx.types.filter_type.clone(),
            "int": vm.ctx.types.int_type.clone(),
            "list": vm.ctx.types.list_type.clone(),
            "map": vm.ctx.types.map_type.clone(),
            "memoryview": vm.ctx.types.memoryview_type.clone(),
            "object": vm.ctx.types.object_type.clone(),
            "property": vm.ctx.types.property_type.clone(),
            "range": vm.ctx.types.range_type.clone(),
            "set": vm.ctx.types.set_type.clone(),
            "slice": vm.ctx.types.slice_type.clone(),
            "staticmethod": vm.ctx.types.staticmethod_type.clone(),
            "str": vm.ctx.types.str_type.clone(),
            "super": vm.ctx.types.super_type.clone(),
            "tuple": vm.ctx.types.tuple_type.clone(),
            "type": vm.ctx.types.type_type.clone(),
            "zip": vm.ctx.types.zip_type.clone(),
            # // Constants
            "None": vm.ctx.get_none(),
            "True": vm.ctx.new_bool(True),
            "False": vm.ctx.new_bool(False),
            "NotImplemented": vm.ctx.get_not_implemented(),
            "Ellipsis": vm.ctx.ellipsis.clone(),
            # // ordered by exception_hierarachy.txt
            # // Exceptions:
            "BaseException": vm.ctx.exceptions.base_exception_type.clone(),
            "SystemExit": vm.ctx.exceptions.system_exit.clone(),
            "KeyboardInterrupt": vm.ctx.exceptions.keyboard_interrupt.clone(),
            "GeneratorExit": vm.ctx.exceptions.generator_exit.clone(),
            "Exception": vm.ctx.exceptions.exception_type.clone(),
            "StopIteration": vm.ctx.exceptions.stop_iteration.clone(),
            "StopAsyncIteration": vm.ctx.exceptions.stop_async_iteration.clone(),
            "ArithmeticError": vm.ctx.exceptions.arithmetic_error.clone(),
            "FloatingPointError": vm.ctx.exceptions.floating_point_error.clone(),
            "OverflowError": vm.ctx.exceptions.overflow_error.clone(),
            "ZeroDivisionError": vm.ctx.exceptions.zero_division_error.clone(),
            "AssertionError": vm.ctx.exceptions.assertion_error.clone(),
            "AttributeError": vm.ctx.exceptions.attribute_error.clone(),
            "BufferError": vm.ctx.exceptions.buffer_error.clone(),
            "EOFError": vm.ctx.exceptions.eof_error.clone(),
            "ImportError": vm.ctx.exceptions.import_error.clone(),
            "ModuleNotFoundError": vm.ctx.exceptions.module_not_found_error.clone(),
            "LookupError": vm.ctx.exceptions.lookup_error.clone(),
            "IndexError": vm.ctx.exceptions.index_error.clone(),
            "KeyError": vm.ctx.exceptions.key_error.clone(),
            "MemoryError": vm.ctx.exceptions.memory_error.clone(),
            "NameError": vm.ctx.exceptions.name_error.clone(),
            "UnboundLocalError": vm.ctx.exceptions.unbound_local_error.clone(),
            "OSError": vm.ctx.exceptions.os_error.clone(),
            # // OSError alias
            "IOError": vm.ctx.exceptions.os_error.clone(),
            "EnvironmentError": vm.ctx.exceptions.os_error.clone(),
            "BlockingIOError": vm.ctx.exceptions.blocking_io_error.clone(),
            "ChildProcessError": vm.ctx.exceptions.child_process_error.clone(),
            "ConnectionError": vm.ctx.exceptions.connection_error.clone(),
            "BrokenPipeError": vm.ctx.exceptions.broken_pipe_error.clone(),
            "ConnectionAbortedError": vm.ctx.exceptions.connection_aborted_error.clone(),
            "ConnectionRefusedError": vm.ctx.exceptions.connection_refused_error.clone(),
            "ConnectionResetError": vm.ctx.exceptions.connection_reset_error.clone(),
            "FileExistsError": vm.ctx.exceptions.file_exists_error.clone(),
            "FileNotFoundError": vm.ctx.exceptions.file_not_found_error.clone(),
            "InterruptedError": vm.ctx.exceptions.interrupted_error.clone(),
            "IsADirectoryError": vm.ctx.exceptions.is_a_directory_error.clone(),
            "NotADirectoryError": vm.ctx.exceptions.not_a_directory_error.clone(),
            "PermissionError": vm.ctx.exceptions.permission_error.clone(),
            "ProcessLookupError": vm.ctx.exceptions.process_lookup_error.clone(),
            "TimeoutError": vm.ctx.exceptions.timeout_error.clone(),
            "ReferenceError": vm.ctx.exceptions.reference_error.clone(),
            "RuntimeError": vm.ctx.exceptions.runtime_error.clone(),
            "NotImplementedError": vm.ctx.exceptions.not_implemented_error.clone(),
            "RecursionError": vm.ctx.exceptions.recursion_error.clone(),
            "SyntaxError": vm.ctx.exceptions.syntax_error.clone(),
            "IndentationError": vm.ctx.exceptions.indentation_error.clone(),
            "TabError": vm.ctx.exceptions.tab_error.clone(),
            "SystemError": vm.ctx.exceptions.system_error.clone(),
            "TypeError": vm.ctx.exceptions.type_error.clone(),
            "ValueError": vm.ctx.exceptions.value_error.clone(),
            "UnicodeError": vm.ctx.exceptions.unicode_error.clone(),
            "UnicodeDecodeError": vm.ctx.exceptions.unicode_decode_error.clone(),
            "UnicodeEncodeError": vm.ctx.exceptions.unicode_encode_error.clone(),
            "UnicodeTranslateError": vm.ctx.exceptions.unicode_translate_error.clone(),
            # // Warnings
            "Warning": vm.ctx.exceptions.warning.clone(),
            "DeprecationWarning": vm.ctx.exceptions.deprecation_warning.clone(),
            "PendingDeprecationWarning": vm.ctx.exceptions.pending_deprecation_warning.clone(),
            "RuntimeWarning": vm.ctx.exceptions.runtime_warning.clone(),
            "SyntaxWarning": vm.ctx.exceptions.syntax_warning.clone(),
            "UserWarning": vm.ctx.exceptions.user_warning.clone(),
            "FutureWarning": vm.ctx.exceptions.future_warning.clone(),
            "ImportWarning": vm.ctx.exceptions.import_warning.clone(),
            "UnicodeWarning": vm.ctx.exceptions.unicode_warning.clone(),
            "BytesWarning": vm.ctx.exceptions.bytes_warning.clone(),
            "ResourceWarning": vm.ctx.exceptions.resource_warning.clone(),
            "EncodingWarning": vm.ctx.exceptions.encoding_warning.clone(),
        },
    )
