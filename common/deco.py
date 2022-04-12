from __future__ import annotations
from dataclasses import dataclass
import enum
import inspect
from typing import TYPE_CHECKING, Any, Callable, Optional, TypeVar
import importlib


if TYPE_CHECKING:
    from vm.function_ import FuncArgs
    from vm.pyobjectrc import PyObjectRef
    from vm.vm import VirtualMachine

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


# TODO
def pymodule(cls):
    funcs = {}
    members = inspect.getmembers(cls)
    for name, mem in members:
        if name.startswith("__") and name.startswith("__"):
            continue
        if not inspect.isfunction(mem):
            continue
        fn = getattr(mem, "pyfunction", None)
        assert fn is not None, f"method {name} isnt a `pyfunction`"
        funcs[name] = fn
    cls.pyfunctions = funcs
    return cls


TYPE2MODULE = {
    "PyStr": "vm.builtins.pystr",
    "ArgIterable": "vm.function.arguments",
    "ArgMapping": "vm.function.arguments",
    "ArgCallable": "vm.function.arguments",
}


@dataclass
class TypeProxy:
    name: str
    module: str
    typ: Optional[Any]
    is_optional: bool

    @staticmethod
    def from_annotation(annotation: str) -> Optional[TypeProxy]:
        name = annotation
        is_optional = False
        if name.startswith("Optional["):
            name = name[len("Optional[") : -1]
            is_optional = True
        name = name.rsplit(".", 1)[-1]
        if name in ("PyObject", "PyObjectRef", "PyRef"):
            return TypeProxy("PyRef", module="", typ=None, is_optional=is_optional)
        elif name.startswith("PyRef["):
            name = name[len("PyRef[") : -1]
        elif name.endswith("Ref"):
            name = name[: -len("Ref")]

        assert "[" not in name and "]" not in name, (annotation, name)
        module = TYPE2MODULE.get(name)
        if module is None:
            return None
        return TypeProxy(name, module=module, typ=None, is_optional=is_optional)

    def try_from_object(self, vm: VirtualMachine, obj: PyObjectRef):
        if self.name == "PyRef":
            return obj
        if self.typ is None:
            self.typ = __import__(self.module, fromlist=[self.name])
        return self.typ.try_from_object(vm, obj)


def make_cast(
    annotation: type | str,
) -> Callable[[VirtualMachine, PyObjectRef], PyObjectRef]:
    if isinstance(annotation, str):
        proxy = TypeProxy.from_annotation(annotation)
        assert proxy is not None
        return proxy.try_from_object
    else:
        return lambda vm, obj: annotation.try_from_object(vm, obj)


def pyfunction(f):
    sig = inspect.signature(f, eval_str=False)
    casts = {n: make_cast(p.annotation) for n, p in sig.parameters.items() if n != "vm"}

    def foo(vm: VirtualMachine, fargs: FuncArgs) -> PyObjectRef:
        bs = sig.bind(*fargs.args, **fargs.kwargs, vm=vm)
        res = f(
            *(casts[name](vm, obj) for name, obj in zip(bs.arguments, bs.args)),
            **{k: casts[k](vm, v) for k, v in bs.kwargs.items() if k != "vm"},
            vm=vm,
        )
        return vm.unwrap_or_none(res)

    f.__func__.pyfunction = foo
    return f
