from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
import dataclasses
import enum
from typing import TYPE_CHECKING, Any, Callable, Optional, Type, TypeVar, Union
from common.deco import pymethod, pyslot
from common.hash import PyHash
if TYPE_CHECKING:
    from vm.builtins.pystr import PyStrRef
    from vm.builtins.pytype import PyTypeRef
    from vm.function_ import FuncArgs
    from vm.protocol.iter import PyIterReturn
    from vm.protocol.mapping import PyMappingMethods
    from vm.protocol.sequence import PySequenceMethods
    from vm.pyobject import PyComparisonValue
    from vm.protocol.buffer import PyBuffer

    from vm.pyobjectrc import PyObject, PyObjectRef, PyRef
    from vm.vm import VirtualMachine

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


def iter_wrapper(zelf: PyObjectRef, vm: VirtualMachine) -> PyObjectRef:
    return vm.call_special_method(zelf, "__iter__", FuncArgs.empty())


# TODO impl `*_wrapper()`

T = TypeVar("T")


# class PTComparableProtocol(PTProtocol):
#     @classmethod
#     def class_(cls, vm: VirtualMachine) -> PyTypeRef:
#         ...

#     # @classmethod
#     # def special_retrieve(cls: Type[T], vm: VirtualMachine, obj: PyObjectRef) -> PyRef[T]:
#     #     ...

#     @classmethod
#     def try_from_object(cls: Type[T], vm: VirtualMachine, obj: PyObjectRef) -> T:
#         ...

#     @classmethod
#     def cmp(
#         cls: Type[T],
#         zelf: PyRef[T],
#         other: PyObject,
#         op: PyComparisonValue,
#         vm: VirtualMachine,
#     ) -> PyComparisonValue:
#         ...


# PTC = TypeVar("PTC", bound=PTComparableProtocol)


HashableT = TypeVar("HashableT", contravariant=True, bound="HashableMixin")


@dataclass
class HashableMixin(ABC):
    @pyslot()
    @classmethod
    def slot_hash(cls: Any, zelf: PyObject, vm: VirtualMachine) -> PyHash:
        if (zelf_ := zelf.downcast_ref(cls)) is not None:
            return cls.hash(zelf_, vm)
        else:
            vm.new_type_error("unexpected payload for __hash__")

    @pymethod()
    @classmethod
    def i__hash__(cls, zelf: PyObjectRef, vm: VirtualMachine) -> PyObjectRef:
        return vm.ctx.new_int(cls.slot_hash(zelf, vm))

    @classmethod
    @abstractmethod
    # @classmethod
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

    @pyslot()
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

    @pymethod()
    @classmethod
    def i__eq__(
        cls: Type[ContravariantT],
        zelf: PyRef[ContravariantT],
        other: PyObject,
        vm: VirtualMachine,
    ) -> PyObjectRef:
        return cmp_to_pyobject(cls.cmp(zelf, other, PyComparisonOp.Eq, vm), vm)

    @pymethod()
    @classmethod
    def i__ne__(
        cls: Type[ContravariantT],
        zelf: PyRef[ContravariantT],
        other: PyObject,
        vm: VirtualMachine,
    ) -> PyObjectRef:
        return cmp_to_pyobject(cls.cmp(zelf, other, PyComparisonOp.Ne, vm), vm)

    @pymethod()
    @classmethod
    def i__lt__(
        cls: Type[ContravariantT],
        zelf: PyRef[ContravariantT],
        other: PyObject,
        vm: VirtualMachine,
    ) -> PyObjectRef:
        return cmp_to_pyobject(cls.cmp(zelf, other, PyComparisonOp.Lt, vm), vm)

    @pymethod()
    @classmethod
    def i__le__(
        cls: Type[ContravariantT],
        zelf: PyRef[ContravariantT],
        other: PyObject,
        vm: VirtualMachine,
    ) -> PyObjectRef:
        return cmp_to_pyobject(cls.cmp(zelf, other, PyComparisonOp.Le, vm), vm)

    @pymethod()
    @classmethod
    def i__ge__(
        cls: Type[ContravariantT],
        zelf: PyRef[ContravariantT],
        other: PyObject,
        vm: VirtualMachine,
    ) -> PyObjectRef:
        return cmp_to_pyobject(cls.cmp(zelf, other, PyComparisonOp.Ge, vm), vm)

    @pymethod()
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
        cls, class_: PyTypeRef, args: FuncArgs, vm: VirtualMachine
    ) -> PyObjectRef:
        ...

    @pyslot()
    @classmethod
    def slot_new(
        cls, class_: PyTypeRef, args: FuncArgs, *, vm: VirtualMachine
    ) -> PyObjectRef:
        return cls.py_new(class_, args, vm)


@dataclass
class GetDescriptorMixin(ABC):
    @staticmethod
    @abstractmethod
    def descr_get(
        zelf: PyObjectRef,
        obj: Optional[PyObjectRef],
        cls: Optional[PyObjectRef],
        vm: VirtualMachine,
    ) -> PyObjectRef:
        ...

    @pymethod()
    @staticmethod
    def i__get__(
        zelf: PyObjectRef,
        obj: PyObjectRef,
        cls: Optional[PyObjectRef],
        *,
        vm: VirtualMachine,
    ) -> PyObjectRef:
        raise NotImplementedError

    @staticmethod
    def _zelf(zelf: PyObjectRef, t: Type[T], vm: VirtualMachine) -> PyRef[T]:
        raise NotImplementedError
        # return zelf.try_into_value(t, vm)  # type: ignore

    @classmethod
    def _unwrap(
        cls,
        zelf: PyObjectRef,
        t: Type[T],
        obj: Optional[PyObjectRef],
        vm: VirtualMachine,
    ) -> tuple[PyRef[T], PyObjectRef]:
        return (cls._zelf(zelf, t, vm), vm.unwrap_or_none(obj))
