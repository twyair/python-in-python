from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
import dataclasses
import enum
from typing import TYPE_CHECKING, Any, Callable, Optional, Type, TypeVar, Union


if TYPE_CHECKING:
    from vm.protocol.sequence import PySequence
    from vm.builtins.pystr import PyStrRef
    from vm.builtins.pytype import PyTypeRef
    from vm.function_ import FuncArgs
    from vm.protocol.iter import PyIterReturn
    from vm.protocol.mapping import PyMappingMethods
    from vm.protocol.sequence import PySequenceMethods
    from vm.pyobject import PyComparisonValue
    from vm.protocol.buffer import PyBuffer
    from vm.protocol.mapping import PyMapping

    from vm.pyobjectrc import PyObject, PyObjectRef, PyRef
    from vm.vm import VirtualMachine

from common.deco import pymethod, pyslot
from common.error import PyImplBase, PyImplError, PyImplException, unreachable
from common.hash import PyHash

#

# import vm.pyobjectrc as prc

SLOTS = {
    # "name",
    "as_sequence",
    "as_mapping",
    "hash",
    "call",
    "getattro",
    "setattro",
    "as_buffer",
    "richcompare",
    "iter",
    "iternext",
    # "doc",
    "descr_get",
    "descr_set",
    "new",
    "del",
}


@dataclass
class PyTypeSlots:
    flags: PyTypeFlags
    name: Optional[str] = None
    as_sequence: Optional[AsSequenceFunc] = None
    as_mapping: Optional[AsMappingFunc] = None
    hash: Optional[HashFunc] = None
    call: Optional[GenericMethod] = None
    getattro: Optional[GetattroFunc] = None
    setattro: Optional[SetattroFunc] = None
    as_buffer: Optional[AsBufferFunc] = None
    richcompare: Optional[RichCompareFunc] = None
    iter: Optional[IterFunc] = None
    iternext: Optional[IterNextFunc] = None
    doc: Optional[str] = None
    descr_get: Optional[DescrGetFunc] = None
    descr_set: Optional[DescrSetFunc] = None
    new: Optional[NewFunc] = None
    del_: Optional[DelFunc] = None

    @staticmethod
    def from_flags(flags: PyTypeFlags) -> PyTypeSlots:
        return PyTypeSlots(flags)

    @staticmethod
    def default() -> PyTypeSlots:
        return PyTypeSlots.from_flags(PyTypeFlags.default())

    def with_(
        self, flags: PyTypeFlags, name: Optional[str], doc: Optional[str]
    ) -> PyTypeSlots:
        return dataclasses.replace(self, flags=flags, name=name, doc=doc)


class PyTypeFlags(enum.Flag):
    EMPTY = 0
    HEAPTYPE = enum.auto()
    BASETYPE = enum.auto()
    METHOD_DESCR = enum.auto()
    HAS_DICT = enum.auto()

    @staticmethod
    def default() -> PyTypeFlags:
        return PyTypeFlags.EMPTY

    def has_feature(self, flag: PyTypeFlags):
        return flag in self


class PyComparisonOp(enum.Enum):
    Lt = "<"
    Gt = ">"
    Ne = "!="
    Eq = "=="
    Le = "<="
    Ge = ">="

    def operator_token(self) -> str:
        return self.value

    def swapped(self) -> PyComparisonOp:
        return SWAP_CMP_OP[self]

    def eq_only(self, f: Callable[[], PyComparisonValue]) -> PyComparisonValue:
        if self == PyComparisonOp.Eq:
            return f()
        elif self == PyComparisonOp.Ne:
            r = f()
            if r.value is not None:
                return PyComparisonValue(not r.value)
            return r
        else:
            return PyComparisonValue(None)

    def method_name(self) -> str:
        return CMP_TO_METHOD_NAME[self]

    def identical_optimization(self, a: PyObjectRef, b: PyObjectRef) -> Optional[bool]:
        return self.map_eq(lambda: a.is_(b))

    def map_eq(self, f: Callable[[], bool]) -> Optional[bool]:
        if self == PyComparisonOp.Eq and f():
            return True
        if self == PyComparisonOp.Ne and f():
            return False
        return None

    def eval_(self, lhs, rhs) -> bool:
        if self == PyComparisonOp.Lt:
            return lhs < rhs
        elif self == PyComparisonOp.Gt:
            return lhs > rhs
        elif self == PyComparisonOp.Le:
            return lhs <= rhs
        elif self == PyComparisonOp.Ge:
            return lhs >= rhs
        elif self == PyComparisonOp.Eq:
            return lhs == rhs
        elif self != PyComparisonOp.Ne:
            return lhs != rhs
        unreachable()


CMP_TO_METHOD_NAME = {
    PyComparisonOp.Lt: "__lt__",
    PyComparisonOp.Gt: "__gt__",
    PyComparisonOp.Ne: "__ne__",
    PyComparisonOp.Eq: "__eq__",
    PyComparisonOp.Le: "__le__",
    PyComparisonOp.Ge: "__ge__",
}

SWAP_CMP_OP = {
    PyComparisonOp.Lt: PyComparisonOp.Gt,
    PyComparisonOp.Gt: PyComparisonOp.Lt,
    PyComparisonOp.Ne: PyComparisonOp.Ne,
    PyComparisonOp.Eq: PyComparisonOp.Eq,
    PyComparisonOp.Le: PyComparisonOp.Ge,
    PyComparisonOp.Ge: PyComparisonOp.Le,
}

GenericMethod = Callable[["PyObject", "FuncArgs", "VirtualMachine"], "PyObjectRef"]
AsMappingFunc = Callable[["PyObject", "VirtualMachine"], "PyMappingMethods"]
HashFunc = Callable[["PyObject", "VirtualMachine"], PyHash]
GetattroFunc = Callable[["PyObjectRef", "PyStrRef", "VirtualMachine"], "PyObjectRef"]
SetattroFunc = Callable[
    ["PyObjectRef", "PyStrRef", Optional["PyObjectRef"], "VirtualMachine"], None
]
AsBufferFunc = Callable[["PyObject", "VirtualMachine"], "PyBuffer"]
RichCompareFunc = Callable[
    ["PyObject", "PyObject", "PyComparisonOp", "VirtualMachine"],
    Union["PyObjectRef", "PyComparisonValue"],
]
IterFunc = Callable[["PyObjectRef", "VirtualMachine"], "PyObjectRef"]
IterNextFunc = Callable[["PyObject", "VirtualMachine"], "PyIterReturn"]
DescrGetFunc = Callable[
    ["PyObjectRef", Optional["PyObjectRef"], Optional["PyObjectRef"], "VirtualMachine"],
    "PyObjectRef",
]
DescrSetFunc = Callable[
    ["PyObjectRef", "PyObjectRef", Optional["PyObjectRef"], "VirtualMachine"], None
]
NewFunc = Callable[["PyTypeRef", "FuncArgs", "VirtualMachine"], "PyObjectRef"]
DelFunc = Callable[["PyObject", "VirtualMachine"], None]
AsSequenceFunc = Callable[["PyObject", "VirtualMachine"], "PySequenceMethods"]


T = TypeVar("T")


# TODO: when intersection types are available change bound to `AsMappingMixin & PyValueMixin`
GetAttrT = TypeVar("GetAttrT", contravariant=True, bound="GetAttrMixin")


@dataclass
class GetAttrMixin(ABC):
    @classmethod
    @abstractmethod
    def getattro(
        cls: Type[GetAttrT],
        zelf: PyRef[GetAttrT],
        name: PyStrRef,
        vm: VirtualMachine,
    ) -> PyObjectRef:
        ...

    @pyslot
    @classmethod
    def slot_getattro(
        cls, obj: PyObjectRef, name: PyStrRef, vm: VirtualMachine
    ) -> PyObjectRef:
        try:
            zelf = obj.downcast(cls)  # type: ignore FIXME
        except PyImplBase as _:
            vm.new_type_error("unexpected payload for __getattribute__")
        else:
            return cls.getattro(zelf, name, vm)  # type: ignore FIXME

    @pymethod(True)
    @classmethod
    def i__getattribute__(
        cls, zelf: PyRef[GetAttrT], name: PyStrRef, vm: VirtualMachine
    ) -> PyObjectRef:
        return cls.getattro(zelf, name, vm)


# TODO: when intersection types are available change bound to `AsMappingMixin & PyValueMixin`
SetAttrT = TypeVar("SetAttrT", contravariant=True, bound="SetAttrMixin")


@dataclass
class SetAttrMixin(ABC):
    @classmethod
    @abstractmethod
    def setattro(
        cls: Type[SetAttrT],
        zelf: PyRef[SetAttrT],
        name: PyStrRef,
        value: Optional[PyObjectRef],
        vm: VirtualMachine,
    ) -> None:
        ...

    @pyslot
    @classmethod
    def slot_setattro(
        cls,
        obj: PyObjectRef,
        name: PyStrRef,
        value: Optional[PyObjectRef],
        vm: VirtualMachine,
    ) -> None:
        if (zelf := obj.downcast_ref(cls)) is not None:  # type: ignore FIXME
            cls.setattro(zelf, name, value, vm)  # type: ignore FIXME
        else:
            vm.new_type_error("unexpected payload for __setattr__")

    @pymethod(True)
    @classmethod
    def i__setattr__(
        cls, zelf: PyRef, name: PyStrRef, value: PyObjectRef, vm: VirtualMachine
    ) -> None:
        cls.setattro(zelf, name, value, vm)

    @pymethod(True)
    @classmethod
    def i__delattr__(cls, zelf: PyRef, name: PyStrRef, vm: VirtualMachine) -> None:
        cls.setattro(zelf, name, None, vm)


# TODO: when intersection types are available change bound to `AsMappingMixin & PyValueMixin`
AsSequenceT = TypeVar("AsSequenceT", contravariant=True, bound="AsSequenceMixin")


@dataclass
class AsSequenceMixin(ABC):
    @classmethod
    @abstractmethod
    def as_sequence(
        cls: Type[AsSequenceT], zelf: PyRef[AsSequenceT], vm: VirtualMachine
    ) -> PySequenceMethods:
        ...

    @pyslot
    @classmethod
    def slot_as_sequence(cls, zelf: PyObject, vm: VirtualMachine) -> PySequenceMethods:
        return cls.as_sequence(zelf.downcast_unchecked_ref(cls), vm)  # type: ignore

    @classmethod
    def sequence_downcast(
        cls: Type[AsSequenceT], seq: PySequence
    ) -> PyRef[AsSequenceT]:
        return seq.obj.downcast_unchecked_ref(cls)  # type: ignore


# TODO: when intersection types are available change bound to `AsMappingMixin & PyValueMixin`
IterableT = TypeVar("IterableT", contravariant=True, bound="IterableMixin")


@dataclass
class IterableMixin(ABC):
    @classmethod
    @abstractmethod
    def iter(
        cls: Type[IterableT], zelf: PyRef[IterableT], vm: VirtualMachine
    ) -> PyObjectRef:
        ...

    @pyslot
    @classmethod
    def slot_iter(cls, zelf: PyObjectRef, vm: VirtualMachine) -> PyObjectRef:
        try:
            r = zelf.downcast(cls)  # type: ignore FIXME?
        except PyImplException as _:
            vm.new_type_error("unexpected payload for __iter__")
        else:
            return cls.iter(r, vm)  # type: ignore FIXME?


# TODO: when intersection types are available change bound to `AsMappingMixin & PyValueMixin`
CallableT = TypeVar("CallableT", contravariant=True, bound="CallableMixin")


@dataclass
class CallableMixin(ABC):
    @classmethod
    @abstractmethod
    def call(
        cls: Type[CallableT], zelf: PyRef[CallableT], args: FuncArgs, vm: VirtualMachine
    ) -> PyObjectRef:
        ...

    @pyslot
    @classmethod
    def slot_call(
        cls, zelf: PyObject, args: FuncArgs, vm: VirtualMachine
    ) -> PyObjectRef:
        r = zelf.downcast_ref(cls)  # type: ignore FIXME?
        if r is None:
            vm.new_type_error("unexpected payload for __call__")
        return cls.call(r, args, vm)  # type: ignore FIXME?

    @pymethod(False)
    @classmethod
    def i__call__(
        cls, zelf: PyObjectRef, args: FuncArgs, vm: VirtualMachine
    ) -> PyObjectRef:
        return cls.slot_call(zelf, args, vm)


@dataclass
class IterNextIterableMixin:
    pass


# TODO: when intersection types are available change bound to `AsMappingMixin & PyValueMixin`
IterNextT = TypeVar("IterNextT", contravariant=True, bound="IterNextMixin")


class IterNextMixin(ABC):
    @classmethod
    @abstractmethod
    def next(
        cls: Type[IterNextT], zelf: PyRef[IterNextT], vm: VirtualMachine
    ) -> PyIterReturn:
        ...

    @pyslot
    @classmethod
    def slot_iternext(cls, zelf: PyObject, vm: VirtualMachine) -> PyIterReturn:
        if (r := zelf.downcast_ref(cls)) is not None:  # type: ignore
            return cls.next(zelf, vm)
        else:
            vm.new_type_error("unexpected payload for __next__")

    @pymethod(True)
    @classmethod
    def i__next__(cls, zelf: PyObjectRef, *, vm: VirtualMachine) -> PyObjectRef:
        return cls.slot_iternext(zelf, vm).into_pyresult(vm)


# TODO: when intersection types are available change bound to `AsMappingMixin & PyValueMixin`
AsMappingT = TypeVar("AsMappingT", contravariant=True, bound="AsMappingMixin")


@dataclass
class AsMappingMixin(ABC):
    @classmethod
    @abstractmethod
    def as_mapping(
        cls: Type[AsMappingT], zelf: PyRef[AsMappingT], vm: VirtualMachine
    ) -> PyMappingMethods:
        ...

    @pyslot
    @classmethod
    def slot_as_mapping(
        cls: Any, zelf: PyObject, vm: VirtualMachine
    ) -> PyMappingMethods:
        return cls.as_mapping(zelf.downcast_unchecked_ref(cls), vm)

    @classmethod
    def mapping_downcast(
        cls: Type[AsMappingT], mapping: PyMapping
    ) -> PyRef[AsMappingT]:
        return mapping.obj.downcast_unchecked_ref(cls)  # type: ignore :(


HashableT = TypeVar("HashableT", contravariant=True, bound="HashableMixin")


@dataclass
class HashableMixin(ABC):
    @pyslot
    @classmethod
    def slot_hash(cls: Any, zelf: PyObject, vm: VirtualMachine) -> PyHash:
        if (zelf_ := zelf.downcast_ref(cls)) is not None:
            return cls.hash(zelf_, vm)
        else:
            vm.new_type_error("unexpected payload for __hash__")

    @pymethod(True)
    @classmethod
    def i__hash__(cls, zelf: PyObjectRef, vm: VirtualMachine) -> PyObjectRef:
        return vm.ctx.new_int(cls.slot_hash(zelf, vm))

    @classmethod
    @abstractmethod
    def hash(
        cls: Type[HashableT], zelf: PyRef[HashableT], vm: VirtualMachine
    ) -> PyHash:
        ...


def cmp_to_pyobject(cmp: PyComparisonValue, vm: VirtualMachine) -> PyObjectRef:
    if cmp.value is None:
        return vm.ctx.get_not_implemented()
    else:
        return vm.ctx.new_bool(cmp.value)


ContravariantT = TypeVar("ContravariantT", contravariant=True, bound="ComparableMixin")


@dataclass
class ComparableMixin(ABC):
    @classmethod
    @abstractmethod
    def cmp(
        cls: Type[ContravariantT],
        zelf: PyRef[ContravariantT],
        other: PyObject,
        op: PyComparisonOp,
        vm: VirtualMachine,
    ) -> PyComparisonValue:
        ...

    @pyslot
    @classmethod
    def slot_richcompare(
        cls: Any,  # FIXME
        zelf: PyObject,
        other: PyObject,
        op: PyComparisonOp,
        vm: VirtualMachine,
    ) -> PyObjectRef:
        if (zelf_ := zelf.downcast_ref(cls)) is not None:
            return cmp_to_pyobject(cls.cmp(zelf_, other, op, vm), vm)
        else:
            vm.new_type_error(f"unexpected payload for {op.method_name()}")

    @pymethod(True)
    @classmethod
    def i__eq__(
        cls: Type[ContravariantT],
        zelf: PyRef[ContravariantT],
        other: PyObject,
        vm: VirtualMachine,
    ) -> PyObjectRef:
        return cmp_to_pyobject(cls.cmp(zelf, other, PyComparisonOp.Eq, vm), vm)

    @pymethod(True)
    @classmethod
    def i__ne__(
        cls: Type[ContravariantT],
        zelf: PyRef[ContravariantT],
        other: PyObject,
        vm: VirtualMachine,
    ) -> PyObjectRef:
        return cmp_to_pyobject(cls.cmp(zelf, other, PyComparisonOp.Ne, vm), vm)

    @pymethod(True)
    @classmethod
    def i__lt__(
        cls: Type[ContravariantT],
        zelf: PyRef[ContravariantT],
        other: PyObject,
        vm: VirtualMachine,
    ) -> PyObjectRef:
        return cmp_to_pyobject(cls.cmp(zelf, other, PyComparisonOp.Lt, vm), vm)

    @pymethod(True)
    @classmethod
    def i__le__(
        cls: Type[ContravariantT],
        zelf: PyRef[ContravariantT],
        other: PyObject,
        vm: VirtualMachine,
    ) -> PyObjectRef:
        return cmp_to_pyobject(cls.cmp(zelf, other, PyComparisonOp.Le, vm), vm)

    @pymethod(True)
    @classmethod
    def i__ge__(
        cls: Type[ContravariantT],
        zelf: PyRef[ContravariantT],
        other: PyObject,
        vm: VirtualMachine,
    ) -> PyObjectRef:
        return cmp_to_pyobject(cls.cmp(zelf, other, PyComparisonOp.Ge, vm), vm)

    @pymethod(True)
    @classmethod
    def i__gt__(
        cls: Type[ContravariantT],
        zelf: PyRef[ContravariantT],
        other: PyObject,
        vm: VirtualMachine,
    ) -> PyObjectRef:
        return cmp_to_pyobject(cls.cmp(zelf, other, PyComparisonOp.Gt, vm), vm)


@dataclass
class ConstructorMixin(ABC):
    @classmethod
    @abstractmethod
    def py_new(
        cls, class_: PyTypeRef, args: FuncArgs, /, vm: VirtualMachine
    ) -> PyObjectRef:
        ...

    @pyslot
    @classmethod
    def slot_new(
        cls, class_: PyTypeRef, args: FuncArgs, vm: VirtualMachine
    ) -> PyObjectRef:
        return cls.py_new(class_, args, vm)


@dataclass
class GetDescriptorMixin(ABC):
    @classmethod
    @abstractmethod
    def descr_get(
        cls,
        zelf: PyObjectRef,
        obj: Optional[PyObjectRef],
        class_: Optional[PyObjectRef],
        vm: VirtualMachine,
    ) -> PyObjectRef:
        ...

    @pyslot
    @classmethod
    def slot_descr_get(
        cls,
        zelf: PyObjectRef,
        obj: Optional[PyObjectRef],
        class_: Optional[PyObjectRef],
        vm: VirtualMachine,
    ) -> PyObjectRef:
        return cls.descr_get(zelf, obj, class_, vm)

    @pymethod(True)
    @classmethod
    def i__get__(
        cls,
        zelf: PyObjectRef,
        obj: PyObjectRef,
        class_: Optional[PyObjectRef],
        *,
        vm: VirtualMachine,
    ) -> PyObjectRef:
        return cls.descr_get(zelf, obj, class_, vm)

    @classmethod
    def _zelf(cls, zelf: PyObjectRef, vm: VirtualMachine) -> PyRef:
        return cls.try_from_object(vm, zelf)  # type: ignore

    @classmethod
    def _unwrap(
        cls,
        zelf: PyObjectRef,
        obj: Optional[PyObjectRef],
        vm: VirtualMachine,
    ) -> tuple[PyRef, PyObjectRef]:
        return (cls._zelf(zelf, vm), vm.unwrap_or_none(obj))

    @classmethod
    def _check(
        cls, zelf: PyObjectRef, obj: Optional[PyObjectRef], vm: VirtualMachine
    ) -> tuple[PyRef, PyObjectRef]:
        if obj is not None:
            return (cls._zelf(zelf, vm), obj)
        else:
            raise PyImplError(zelf)

    @classmethod
    def _cls_is(cls, class_: Optional[PyObjectRef], other: PyObjectRef) -> bool:
        if class_ is None:
            return False
        else:
            return other.is_(class_)


def as_mapping_wrapper(zelf: PyObject, vm: VirtualMachine) -> PyMappingMethods:
    raise NotImplementedError


def as_sequence_wrapper(zelf: PyObject, vm: VirtualMachine) -> PySequenceMethods:
    raise NotImplementedError


def hash_wrapper(zelf: PyObject, vm: VirtualMachine) -> PyHash:
    import vm.builtins.int as pyint

    hash_obj = vm.call_special_method(zelf, "__hash__", FuncArgs())
    if (i := hash_obj.payload_if_subclass(pyint.PyInt, vm)) is not None:
        return i.as_int()
    else:
        vm.new_type_error("__hash__ method should return an integer")


def call_wrapper(zelf: PyObject, args: FuncArgs, vm: VirtualMachine) -> PyObjectRef:
    return vm.call_special_method(zelf, "__call__", args)


def getattro_wrapper(
    zelf: PyObjectRef, name: PyStrRef, vm: VirtualMachine
) -> PyObjectRef:
    return vm.call_special_method(zelf, "__getattribute__", FuncArgs([name]))


def setattro_wrapper(
    zelf: PyObject, name: PyStrRef, value: Optional[PyObjectRef], vm: VirtualMachine
) -> None:
    if value is not None:
        vm.call_special_method(zelf, "__setattr__", FuncArgs([name, value]))
    else:
        vm.call_special_method(zelf, "__delattr__", FuncArgs([name]))


def richcompare_wrapper(
    zelf: PyObject, other: PyObject, op: PyComparisonOp, vm: VirtualMachine
) -> PyObjectRef | PyComparisonValue:
    return vm.call_special_method(zelf, op.method_name(), FuncArgs([other]))


def iter_wrapper(zelf: PyObjectRef, vm: VirtualMachine) -> PyObjectRef:
    return vm.call_special_method(zelf, "__iter__", FuncArgs.empty())


def iternext_wrapper(zelf: PyObject, vm: VirtualMachine) -> PyIterReturn:
    return PyIterReturn.from_pyresult(
        lambda: vm.call_special_method(zelf, "__next__", FuncArgs()), vm
    )


def descr_get_wrapper(
    zelf: PyObjectRef,
    obj: Optional[PyObjectRef],
    cls: Optional[PyObjectRef],
    vm: VirtualMachine,
) -> PyObjectRef:
    return vm.call_special_method(
        # FIXME? is it correct to use `vm.unwrap_or_none` here?
        zelf,
        "__get__",
        FuncArgs([vm.unwrap_or_none(obj), vm.unwrap_or_none(cls)]),
    )


def descr_set_wrapper(
    zelf: PyObjectRef,
    obj: PyObjectRef,
    value: Optional[PyObjectRef],
    vm: VirtualMachine,
) -> None:
    if value is not None:
        vm.call_special_method(zelf, "__set__", FuncArgs([obj, value]))
    else:
        vm.call_special_method(zelf, "__delete__", FuncArgs([obj]))


def new_wrapper(cls: PyTypeRef, args: FuncArgs, vm: VirtualMachine) -> PyObjectRef:
    new = vm.get_attribute_opt(cls.as_object(), vm.mk_str("__new__"))
    assert new is not None
    args.prepend_arg(cls)
    return vm.invoke(new, args)


def del_wrapper(zelf: PyObject, vm: VirtualMachine) -> None:
    vm.call_special_method(zelf, "__del__", FuncArgs())
