from __future__ import annotations
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable, Sequence, TypeAlias

if TYPE_CHECKING:
    from vm.protocol.buffer import PyBuffer
    from vm.pyobjectrc import PyObject, PyObjectRef
    from vm.vm import VirtualMachine


@dataclass
class FuncArgs:
    args: list[PyObjectRef] = field(default_factory=list)
    kwargs: OrderedDict[str, PyObjectRef] = field(default_factory=OrderedDict)

    def into_method_args(self, obj: PyObjectRef, vm: VirtualMachine) -> FuncArgs:
        args = self.into_args(vm)
        args.prepend_arg(obj)
        return args

    def into_args(self, vm: VirtualMachine) -> FuncArgs:
        return self

    def prepend_arg(self, item: PyObjectRef) -> None:
        self.args.insert(0, item)

    @staticmethod
    def empty() -> FuncArgs:
        return FuncArgs([], OrderedDict())

    @staticmethod
    def with_kwargs_names(
        args: Sequence[PyObjectRef], kwarg_names: Sequence[str]
    ) -> FuncArgs:
        total_argc = len(args)
        kwargc = len(kwarg_names)
        posargc = total_argc - kwargc

        posargs = list(args[:posargc])
        kwargs = OrderedDict(zip(kwarg_names, args[posargc:]))

        return FuncArgs(posargs, kwargs)

    def take_positional(self, nargs: int) -> list[PyObjectRef]:
        assert len(self.args) == nargs
        assert not self.kwargs
        return self.args

    def take_positional_arg(self) -> PyObjectRef:
        return self.take_positional(1)[0]


PyNativeFunc: TypeAlias = Callable[["VirtualMachine", FuncArgs], "PyObjectRef"]


@dataclass
class ArgBytesLike:
    value: PyBuffer

    @staticmethod
    def try_from_borrowed_object(vm: VirtualMachine, obj: PyObject) -> ArgBytesLike:
        buffer = PyBuffer.try_from_borrowed_object(vm, obj)
        if buffer.desc.is_contiguous():
            return ArgBytesLike(buffer)
        else:
            vm.new_type_error("non-contiguous buffer is not a bytes-like object")
