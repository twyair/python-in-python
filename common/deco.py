from __future__ import annotations
from dataclasses import dataclass
import enum
import inspect
from typing import TYPE_CHECKING, Any, Callable, Optional, TypeAlias, TypeVar, overload

from common.error import unreachable


if TYPE_CHECKING:
    from vm.function_ import FuncArgs
    from vm.pyobjectrc import PyObjectRef, PyRef
    from vm.vm import VirtualMachine
    from vm.pyobject import PyArithmeticValue, PyValueMixin


def primitive_to_pyobject(
    value: PyRef
    | bool
    | int
    | float
    | complex
    | str
    | bytes
    | PyArithmeticValue[bool | int | float | complex | str | bytes]
    | None,
    vm: VirtualMachine,
) -> PyObjectRef:
    import vm.pyobjectrc as prc  # FIXME?
    import vm.pyobject as po  # FIXME?

    if isinstance(value, prc.PyRef):
        return value
    elif isinstance(value, po.PyValueMixin):
        return value.into_ref(vm)
    elif value is None:
        return vm.ctx.get_none()
    elif isinstance(value, bool):
        return vm.ctx.new_bool(value)
    elif isinstance(value, int):
        return vm.ctx.new_int(value)
    elif isinstance(value, float):
        return vm.ctx.new_float(value)
    elif isinstance(value, complex):
        return vm.ctx.new_complex(value)
    elif isinstance(value, str):
        return vm.ctx.new_str(value)
    elif isinstance(value, bytes):
        return vm.ctx.new_bytes(value)
    elif isinstance(value, po.PyArithmeticValue):
        if value.value is not None:
            return primitive_to_pyobject(value.value, vm)
        else:
            return vm.ctx.get_not_implemented()
    else:
        assert False, type(value)


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
    attrs = {}
    members = inspect.getmembers(cls)
    for name, mem in members:
        orig = name
        if name.startswith("__") and name.endswith("__") or name.startswith("_"):
            continue

        if not inspect.isfunction(mem):
            if name.startswith("attr_"):
                name = name[len("attr_") :]
                assert name not in attrs, name
                loc = mem
                attrs[name] = lambda vm: primitive_to_pyobject(loc, vm)
            else:
                continue
        else:
            if name.startswith("i__") and name.endswith("__"):
                name = name[1:]
            if (fn := getattr(mem, "pyfunction", None)) is not None:
                funcs[name] = fn
            elif (attr := getattr(mem, "pyattr", None)) is not None:
                attrs[name] = attr
            else:
                assert False, f"method {orig} isnt a `pyfunction` nor a `pyattr`"
        # assert fn is not None,
    cls.pyfunctions = funcs
    cls.pyattrs = attrs
    return cls


TYPE2MODULE = {
    "PyStr": "vm.builtins.pystr",
    "PyType": "vm.builtins.pytype",
    "PyInt": "vm.builtins.int",
    "PyFunction": "vm.builtins.function",
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
        import ast

        at = ast.parse(annotation, mode="eval").body
        # print(at.body)
        if isinstance(at, ast.Subscript):
            g = ast.unparse(at.value)
            if g == "Optional":
                is_optional = True
            elif g in ("PyRef", "prc.PyRef"):
                pass
            else:
                assert False, g
            inner = at.slice
        else:
            inner = at
        if isinstance(inner, ast.Name):
            name = inner.id
        elif isinstance(inner, ast.Attribute):
            name = inner.attr
        else:
            assert False, (ast.unparse(inner), inner)

        if name in ("PyObject", "PyObjectRef", "PyRef"):
            return TypeProxy("PyRef", module="", typ=None, is_optional=is_optional)

        name = name.removesuffix("Ref")

        # print(name, annotation)
        module = TYPE2MODULE.get(name)
        if module is None:
            return None
        return TypeProxy(name, module=module, typ=None, is_optional=is_optional)

    def try_from_object(self, vm: VirtualMachine, obj: PyObjectRef):
        import vm.pyobjectrc as prc

        if self.name == "PyRef":
            return obj
        if self.typ is None:
            self.typ = getattr(__import__(self.module, fromlist=[self.name]), self.name)
        ret = self.typ.try_from_object(vm, obj)
        assert isinstance(ret, prc.PyRef), (
            type(ret),
            self.typ.try_from_object,
        )  # TODO: rm
        return ret


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
        if proxy is None and name == "zelf":
            return lambda vm, obj: obj
        assert proxy is not None, annotation
        return proxy.try_from_object
    else:
        unreachable(f"got: '{annotation}' of type '{type(annotation)}'")


@overload
def pyfunction(f: bool) -> Callable[[CT], CT]:
    ...


@overload
def pyfunction(f: CT) -> CT:
    ...


def pyfunction(f):
    cast = True

    def inner(g: CT) -> CT:
        if cast:
            foo = cast_args(g)
        else:
            foo = lambda vm, fargs: g.__func__(fargs, vm=vm)
        g.__func__.pyfunction = foo
        return g

    if isinstance(f, bool):
        cast = f
        return inner
    else:
        return inner(f)


CT_RETURN: TypeAlias = "PyValueMixin | PyObjectRef | str | bytes | bool | int | float | complex | PyArithmeticValue | None"


CT = TypeVar(
    "CT",
    bound="Callable[..., CT_RETURN]",
)


AT = TypeVar("AT", bound="Callable[[VirtualMachine], CT_RETURN]")


def pyattr(f: AT) -> AT:
    f.__func__.pyattr = lambda vm: primitive_to_pyobject(f.__func__(vm), vm)
    return f


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
        return primitive_to_pyobject(res, vm)

    return foo
