from __future__ import annotations
from abc import abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, Type, TypeAlias
from common.hash import PyHash


if TYPE_CHECKING:
    from vm.builtins.bytes import PyBytesRef
    from vm.builtins.pytype import PyTypeRef
    from vm.pyobject import PyContext
    from vm.pyobjectrc import PyRef
    from vm.vm import VirtualMachine
import vm.pyobject as po
import vm.pyobjectrc as prc
import vm.types.slot as slot


@po.tp_flags(basetype=True)
@po.pyimpl(
    constructor=True,
    as_mapping=True,
    as_sequence=True,
    hashable=True,
    comparable=True,
    iterable=True,
)
@po.pyclass("str")
@dataclass
class PyStr(po.PyClassImpl, po.PyValueMixin, po.TryFromObjectMixin, slot.HashableMixin):
    value: str
    # bytes: bytes
    # kind: PyStrKindData
    # hash: PyHash

    @staticmethod
    def class_(vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.str_type

    @staticmethod
    def from_str(s: str, ctx: PyContext) -> PyStrRef:
        return PyStr.new_ref(PyStr(s), ctx)
        # return PyStr.new_ref(PyStr(
        #     bytes=s.encode(),
        #     kind=Utf8(0),  # FIXME
        #     hash=None
        # ), ctx)

    def as_str(self) -> str:
        return self.value

    @staticmethod
    def new_ref(s: PyStr, ctx: PyContext) -> PyStrRef:
        return prc.PyRef.new_ref(s, ctx.types.str_type, None)

    def into_ref(self, vm: VirtualMachine) -> PyStrRef:
        return self.new_ref(self, vm.ctx)

    def as_ref(self) -> str:
        return self.as_str()

    @classmethod
    def hash(
        cls, zelf: PyRef[PyStr], vm: VirtualMachine
    ) -> PyHash:
        # FIXME?
        return hash(zelf.payload.as_str())

    # TODO: impl Constructor for PyStr
    # TODO: impl PyStr @ 323
    # TODO: impl PyStr @ 379
    # TODO: impl Comparable for PyStr
    # TODO: impl Iterable for PyStr
    # TODO: impl AsMapping for PyStr
    # TODO: impl AsSequence for PyStr


# TODO: delete
PyStrRef: TypeAlias = "PyRef[PyStr]"


# @dataclass
# class Ascii:
#     pass


# @dataclass
# class Utf8:
#     value: int


# PyStrKindData = Union[Ascii, Utf8]


@po.pyimpl(constructor=True, iter_next=True)
@po.pyclass("str_iterator")
@dataclass
class PyStrIterator(po.PyClassImpl, po.PyValueMixin):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.str_iterator_type

    # TODO: impl Unconstructible for PyStrIterator
    # TODO: impl IterNextIterable for PyStrIterator
    # TODO: impl IterNext for PyStrIterator


def encode_string(
    s: PyStrRef,
    encoding: Optional[PyStrRef],
    errors: Optional[PyStrRef],
    vm: VirtualMachine,
) -> PyBytesRef:
    raise NotImplementedError


def init(ctx: PyContext) -> None:
    PyStr.extend_class(ctx, ctx.types.str_type)
    PyStrIterator.extend_class(ctx, ctx.types.str_iterator_type)
