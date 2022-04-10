from __future__ import annotations
from dataclasses import dataclass
import enum
from typing import Any, Callable, TypeVar

# from vm.types.slot import SLOTS

T = TypeVar("T")


def pyproperty(
    # *,
    # magic: bool = False,
    # setter: Optional[bool] = None,
    # getter: Optional[bool] = None,
    # name: Optional[str] = None
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    def inner(method: Callable[..., T]) -> Callable[..., T]:
        name = method.__name__
        type = None
        if name.startswith("get_"):
            type = PropertyDescriptorType.GETTER
        elif name.startswith("set_"):
            type = PropertyDescriptorType.SETTER
        elif name.startswith("del_"):
            type = PropertyDescriptorType.DELETER
        else:
            assert False, name
        name = name[4:]
        method.pyimpl_at = PropertyData(MethodData.from_method(method), name, type)

        return method

    return inner


class ImplMethodType(enum.Enum):
    STATIC = enum.auto()
    CLASS = enum.auto()
    INSTANCE = enum.auto()


@dataclass
class MethodData:
    name: str
    method: Callable[..., Any]
    type: ImplMethodType

    @staticmethod
    def from_method(
        method: Callable, type: ImplMethodType = ImplMethodType.INSTANCE
    ) -> MethodData:
        # type = ImplMethodType.STATIC
        # sig = inspect.signature(method)

        name = method.__name__
        assert not name.startswith("__"), name
        if name.startswith("i__") and name.endswith("__"):
            name = name[1:]
        elif name.startswith("r__"):
            name = name[3:]

        return MethodData(name=name, method=method, type=type)


class PropertyDescriptorType(enum.Enum):
    GETTER = enum.auto()
    SETTER = enum.auto()
    DELETER = enum.auto()


@dataclass
class PropertyData:
    method_data: MethodData
    name: str
    descriptor_type: PropertyDescriptorType


@dataclass
class ImplSlotData:
    method_data: MethodData
    name: str


def pymethod(magic: bool = False) -> Callable[[Callable[..., T]], Callable[..., T]]:
    def inner(method: Callable[..., T]) -> Callable[..., T]:
        method_set_data(method, MethodData.from_method(method_get_function(method)))
        return method

    return inner


def pystaticmethod(
    magic: bool = False,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    def inner(method: Callable[..., T]) -> Callable[..., T]:
        method_set_data(
            method,
            MethodData.from_method(method_get_function(method), ImplMethodType.STATIC),
        )
        return method

    return inner


def pyclassmethod(
    magic: bool = False,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    def inner(method: Callable[..., T]) -> Callable[..., T]:
        method_set_data(
            method,
            MethodData.from_method(method_get_function(method), ImplMethodType.CLASS),
        )
        return method

    return inner


def method_get_function(method):
    if isinstance(method, classmethod):
        return method.__func__
    else:
        return method


def method_set_data(method, data) -> None:
    if isinstance(method, classmethod):
        method.__func__.pyimpl_at = data
    else:
        method.pyimpl_at = data


def pyslot() -> Callable[[Callable[..., T]], Callable[..., T]]:
    def inner(method: Callable[..., T]) -> Callable[..., T]:
        prefix = "slot_"
        name = method.__name__
        assert name.startswith(prefix)
        name = name[len(prefix) :]
        # assert name in SLOTS
        method_set_data(
            method,
            ImplSlotData(MethodData.from_method(method_get_function(method)), name),
        )

        return method

    return inner
