from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Final
from common.error import PyImplBase, PyImplError, PyImplException
if TYPE_CHECKING:
    from vm.builtins.tuple import PyTupleRef
    from vm.exceptions import PyBaseException
    from vm.function_ import FuncArgs, PyNativeFunc
    from vm.pyobject import PyContext
    from vm.pyobjectrc import PyObject, PyObjectRef
    from vm.vm import VirtualMachine


def strict_errors(err: PyObjectRef, vm: VirtualMachine) -> PyObjectRef:
    try:
        e = err.downcast(PyBaseException)
    except PyImplBase as _:
        vm.new_type_error("codec must pass exception instance")
    raise PyImplException(e)


def make_native_func(
    f: Callable[[PyObjectRef, VirtualMachine], PyObjectRef]
) -> PyNativeFunc:
    def foo(vm: VirtualMachine, args: FuncArgs) -> PyObjectRef:
        return f(args.take_positional_arg(), vm)

    return foo


# TODO: delete
def nop(vm: VirtualMachine, args: FuncArgs) -> PyObjectRef:
    vm.new_type_error("TODO")


@dataclass
class CodecsRegistry:
    inner: RegistryInner

    @staticmethod
    def new(ctx: PyContext) -> CodecsRegistry:

        errors = {
            "strict": ctx.new_function(
                ctx.new_str("strict_errors").payload,
                make_native_func(strict_errors),
            ),
            "ignore": ctx.new_function(
                ctx.new_str("ignore_errors").payload, nop  # FIXME: ignore_errors
            ),
            "replace": ctx.new_function(
                ctx.new_str("replace_errors").payload,
                nop,  # FIXME! replace_errors
            ),
            "xmlcharrefreplace": ctx.new_function(
                ctx.new_str("xmlcharrefreplace_errors").payload,
                nop,  # FIXME! xmlcharrefreplace_errors,
            ),
            "backslashreplace": ctx.new_function(
                ctx.new_str("backslashreplace_errors").payload,
                nop,  # FIXME! backslashreplace_errors,
            ),
            "namereplace": ctx.new_function(
                ctx.new_str("namereplace_errors").payload,
                nop,  # FIXME! namereplace_errors
            ),
            "surrogatepass": ctx.new_function(
                ctx.new_str("surrogatepass_errors").payload,
                nop,  # FIXME! surrogatepass_errors
            ),
            "surrogateescape": ctx.new_function(
                ctx.new_str("surrogateescape_errors").payload,
                nop,  # FIXME! surrogateescape_errors
            ),
        }
        inner = RegistryInner(search_path=[], search_cache={}, errors=errors)
        return CodecsRegistry(inner)


@dataclass
class RegistryInner:
    search_path: list[PyObjectRef]
    search_cache: dict[str, PyCodec]
    errors: dict[str, PyObjectRef]


DEFAULT_ENCODING: Final[str] = "utf-8"


@dataclass
class PyCodec:
    value: PyTupleRef

    @staticmethod
    def from_tuple(tuple: PyTupleRef) -> PyCodec:
        if len(tuple.payload) != 4:
            PyImplError(tuple)
        return PyCodec(tuple)

    def into_tuple(self) -> PyTupleRef:
        return self.value

    def as_tuple(self) -> PyTupleRef:
        return self.value

    def get_encode_func(self) -> PyObject:
        return self.value.payload.as_slice()[0]

    def get_decode_func(self) -> PyObject:
        return self.value.payload.as_slice()[1]

    def is_text_codec(self, vm: VirtualMachine) -> bool:
        is_text = vm.get_attribute_opt(self.value, vm.mk_str("_is_text_encoding"))
        if is_text is None:
            return True
        return is_text.try_to_bool(vm)

    # TODO: oo methods
