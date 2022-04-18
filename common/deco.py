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
    from vm.pyobject import PyArithmeticValue

# from vm.types.slot import SLOTS

T = TypeVar("T")


def pyproperty() -> Callable[[CT], CT]:
    def inner(method: CT) -> CT:
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
        method.pyimpl_at = PropertyData(
            MethodData.from_method(method, ImplMethodType.INSTANCE, cast=False),
            name,
            type,
        )

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
    # cast: bool
    # casts: Callable[[VirtualMachine, FuncArgs], PyObjectRef]
    casts: Optional[dict[str, Callable[[VirtualMachine, PyObjectRef], PyObjectRef]]]

    @staticmethod
    def from_method(method: Callable, type: ImplMethodType, cast: bool) -> MethodData:
        func = method_get_function(method)
        # if cast:
        #     foo = cast_args(method)
        # else:
        #     foo = method

        name = method.__name__
        assert not name.startswith("__"), name
        if name.startswith("i__") and name.endswith("__"):
            name = name[1:]
        elif name.startswith("r__"):
            name = name[3:]

        return MethodData(
            name=name, method=method, type=type, casts=get_casts(func) if cast else None
        )


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


def pymethod(cast: bool) -> Callable[[CT], CT]:
    def inner(method: CT) -> CT:
        method_set_data(
            method,
            MethodData.from_method(method, type=ImplMethodType.INSTANCE, cast=cast),
        )
        return method

    return inner


def pystaticmethod(
    cast: bool,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    def inner(method: Callable[..., T]) -> Callable[..., T]:
        method_set_data(
            method,
            MethodData.from_method(method, ImplMethodType.STATIC, cast=cast),
        )
        return method

    return inner


def pyclassmethod(
    cast: bool,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    def inner(method: Callable[..., T]) -> Callable[..., T]:
        method_set_data(
            method,
            MethodData.from_method(method, ImplMethodType.CLASS, cast=cast),
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
    elif isinstance(method, staticmethod):
        method.__func__.pyimpl_at = data
    else:
        method.pyimpl_at = data


RT = TypeVar("RT", bound=Callable)


def pyslot(method: RT) -> RT:
    prefix = "slot_"
    name = method.__name__
    assert name.startswith(prefix)
    name = name[len(prefix) :]
    # assert name in SLOTS
    method_set_data(
        method,
        ImplSlotData(
            MethodData.from_method(method, ImplMethodType.INSTANCE, cast=False),
            name,
        ),
    )

    return method


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
    "PyType": "vm.builtins.pytype",
    "PyInt": "vm.builtins.int",
    "SetIterable": "vm.builtins.set",
    "ArgIterable": "vm.function.arguments",
    "ArgMapping": "vm.function.arguments",
    "ArgCallable": "vm.function.arguments",
    "ArgBytesLike": "vm.function.arguments",
    "ArgIterable": "vm.function.arguments",
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


def cast_to_int(vm: VirtualMachine, obj: PyObjectRef, /) -> int:
    return vm.to_index(obj)._.as_int()


def make_cast(
    name: str,
    annotation: str,
) -> Callable[[VirtualMachine, PyObjectRef], Any]:
    if isinstance(annotation, str):
        if annotation in ("int", "Optional[int]"):
            return cast_to_int
        proxy = TypeProxy.from_annotation(annotation)
        if proxy is None and name == "zelf":  # TODO: del
            return lambda vm, obj: obj
        assert proxy is not None, annotation
        return proxy.try_from_object
    else:
        raise NotImplementedError(f"got: {annotation}")
        # return lambda vm, obj: annotation.try_from_object(vm, obj)  # type: ignore


def pyfunction(f: CT) -> CT:
    foo = cast_args(f)
    f.__func__.pyfunction = foo
    return f


CT = TypeVar(
    "CT",
    bound="Callable[..., PyObjectRef | str | bool | int | float | complex | PyArithmeticValue | None]",
)


def get_casts(
    f: Callable,
) -> dict[str, Callable[[VirtualMachine, PyObjectRef], PyObjectRef]]:
    sig = inspect.signature(f, eval_str=False)
    return {
        n: make_cast(n, p.annotation)
        for n, p in sig.parameters.items()
        if n not in ("vm", "cls", "self")
    }


def cast_args(f: Callable) -> Callable[[VirtualMachine, FuncArgs], PyObjectRef]:
    sig = inspect.signature(f, eval_str=False)
    casts = get_casts(f)

    def foo(vm: VirtualMachine, fargs: FuncArgs) -> PyObjectRef:
        bs = sig.bind(*fargs.args, **fargs.kwargs, vm=vm)
        res = f(
            *(casts[name](vm, obj) for name, obj in zip(bs.arguments, bs.args)),
            **{k: casts[k](vm, v) for k, v in bs.kwargs.items() if k != "vm"},
            vm=vm,
        )
        return vm.unwrap_or_none(res)

    return foo
