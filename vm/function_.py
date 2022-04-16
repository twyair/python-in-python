from __future__ import annotations
from collections import OrderedDict
from dataclasses import dataclass, field
import inspect
from typing import (
    TYPE_CHECKING,
    Callable,
    Optional,
    Sequence,
    TypeAlias,
)

if TYPE_CHECKING:
    from vm.protocol.buffer import PyBuffer
    from vm.pyobjectrc import PyObject, PyObjectRef
    from vm.vm import VirtualMachine


@dataclass
# class BoundArgs:
#     spec: ArgsSpec
#     signature_name: str
#     args: dict[str, PyObjectRef]
#     # args_obj: inspect.BoundArguments

#     # def get(self, signature_name: str) -> Optional[inspect.BoundArguments]:
#     #     assert signature_name in self.spec.signatures, (
#     #         signature_name,
#     #         self.spec.signatures,
#     #     )
#     #     if signature_name == self.signature_name:
#     #         return self.args
#     #     else:
#     #         return None

#     def is_(self, name: str) -> bool:
#         assert name in self.spec.signatures, (name, self.spec.signatures.keys())
#         return self.signature_name == name

#     def __getattr__(self, name: str) -> PyObjectRef:
#         return self.args[name]


# @dataclass
# class signature:
#     value: inspect.Signature

#     def __init__(self, func: Callable[..., None]) -> None:
#         self.value = inspect.signature(func)

#     def bind(self, fargs: FuncArgs, apply_defaults=True) -> inspect.BoundArguments:
#         return fargs.bind(self, apply_defaults=apply_defaults)


# @dataclass
# class ArgsSpec:
#     signatures: dict[str, Signature]

#     def bind_or_none(self, args: FuncArgs, /) -> Optional[BoundArgs]:
#         for name, sig in self.signatures.items():
#             try:
#                 bs = sig.value.bind(*args.args, **args.kwargs)
#             except TypeError as _:
#                 pass
#             else:
#                 return BoundArgs(self, name, bs.arguments)
#         return None

#     def bind(self, args: FuncArgs, /, vm: VirtualMachine) -> BoundArgs:
#         r = self.bind_or_none(args)
#         if r is None:
#             # TODO: improve error message
#             vm.new_type_error("wrong arguments")
#         return r


# def args_spec(cls) -> ArgsSpec:
#     signatures = {}

#     for name, mem in inspect.getmembers(cls):
#         if inspect.isfunction(mem) and not name.startswith("__"):
#             sig = inspect.signature(mem)
#             for n, p in sig.parameters.items():
#                 assert (
#                     p.default is inspect._empty
#                 ), f"parameter {n} of method {name} has a default value"
#             signatures[name] = sig

#     return ArgsSpec(signatures)


# @args_spec
# class args_spec_single_optional_positional_only:
#     @staticmethod
#     def none():
#         ...

#     @staticmethod
#     def one(x, /):
#         ...


# @args_spec
# class args_spec_none:
#     @staticmethod
#     def none():
#         ...


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

    def take_positional_range(
        self, start: int, stop: int
    ) -> Optional[list[PyObjectRef]]:
        if self.kwargs or not (start <= len(self.args) <= stop):
            return None
        return self.args

    def take_positional_optional(
        self, on_error: Callable[[], PyObjectRef]
    ) -> Optional[PyObjectRef]:
        args = self.take_positional_range(0, 1)
        if args is None:
            return on_error()
        return args[0]

    def bind(self, func: Callable) -> inspect.BoundArguments:
        args = inspect.signature(func).bind(*self.args, **self.kwargs)
        args.apply_defaults()
        return args

    # def bind(
    #     self, sig: signature, apply_defaults: bool = True
    # ) -> inspect.BoundArguments:
    #     args = sig.value.bind(*self.args, **self.kwargs)
    #     if apply_defaults:
    #         args.apply_defaults()
    #     return args


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
