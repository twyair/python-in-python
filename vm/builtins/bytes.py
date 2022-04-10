from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar, Optional, TypeAlias
from common.deco import pyclassmethod, pymethod, pystaticmethod

if TYPE_CHECKING:
    from vm.builtins.iter import PositionIterInternal
    from vm.builtins.pytype import PyTypeRef
    from vm.function_ import ArgBytesLike
    from vm.pyobject import (
        PyClassImpl,
        PyContext,
        PyValueMixin,
        pyclass,
        pyimpl,
        tp_flags,
    )
    from vm.pyobjectrc import PyObject, PyObjectRef, PyRef
    from vm.types.slot import PyTypeFlags
    from vm.vm import VirtualMachine
import vm.pyobject as po


@po.tp_flags(basetype=True)
@po.pyimpl(
    constructor=True,
    as_mapping=True,
    as_sequence=True,
    hashable=True,
    comparable=True,
    as_buffer=True,
    iterable=True,
)
@po.pyclass("bytes")
@dataclass
class PyBytes(po.PyClassImpl, po.PyValueMixin):
    inner: bytes

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.bytes_type

    @staticmethod
    def new_ref(value: bytes, ctx: PyContext) -> PyBytesRef:
        return PyRef.new_ref(PyBytes(value), ctx.types.tuple_type, None)

    @pymethod()
    def i__repr__(self, *, vm: VirtualMachine) -> PyObjectRef:
        return vm.mk_str(repr(self.inner))

    @pymethod()
    def i__len__(self, *, vm: VirtualMachine) -> PyObjectRef:
        return vm.ctx.new_int(len(self.inner))

    # @pymethod()
    # def bytes()

    @pymethod()
    def i__sizeof__(self, *, vm: VirtualMachine) -> PyObjectRef:
        return vm.ctx.new_int(self.__sizeof__())

    @pymethod()
    def i__add__(self, other: PyObjectRef, *, vm: VirtualMachine) -> PyObjectRef:
        arg = ArgBytesLike.try_from_borrowed_object(vm, other)
        return vm.ctx.new_bytes(self.inner + arg.value.methods.obj_bytes(arg.value))

    @pymethod()
    def i__contains__(self, needle: PyObjectRef, vm) -> PyObjectRef:
        raise NotImplementedError

    @pystaticmethod()
    @staticmethod
    def maketrans(frm: PyObjectRef, to: PyObjectRef, vm: VirtualMachine) -> PyObjectRef:
        raise NotImplementedError

    def _getitem(self, needle: PyObject, vm: VirtualMachine) -> SequenceIndex:
        raise NotImplementedError

    @pymethod()
    def i__getitem__(self, needle: PyObjectRef, vm: VirtualMachine) -> PyObjectRef:
        return self._getitem(needle, vm)

    @pymethod()
    def isalnum(self, vm: VirtualMachine) -> PyObjectRef:
        return vm.ctx.new_bool(self.inner.isalnum())

    @pymethod()
    def isalpha(self, vm: VirtualMachine) -> PyObjectRef:
        return vm.ctx.new_bool(self.inner.isalpha())

    @pymethod()
    def isascii(self, vm: VirtualMachine) -> PyObjectRef:
        return vm.ctx.new_bool(self.inner.isascii())

    @pymethod()
    def isdigit(self, vm: VirtualMachine) -> PyObjectRef:
        return vm.ctx.new_bool(self.inner.isdigit())

    @pymethod()
    def islower(self, vm: VirtualMachine) -> PyObjectRef:
        return vm.ctx.new_bool(self.inner.islower())

    @pymethod()
    def isspace(self, vm: VirtualMachine) -> PyObjectRef:
        return vm.ctx.new_bool(self.inner.isspace())

    @pymethod()
    def isupper(self, vm: VirtualMachine) -> PyObjectRef:
        return vm.ctx.new_bool(self.inner.isupper())

    @pymethod()
    def istitle(self, vm: VirtualMachine) -> PyObjectRef:
        return vm.ctx.new_bool(self.inner.istitle())

    @pymethod()
    def lower(self, vm: VirtualMachine) -> PyObjectRef:
        return vm.ctx.new_bytes(self.inner.lower())

    @pymethod()
    def upper(self, vm: VirtualMachine) -> PyObjectRef:
        return vm.ctx.new_bytes(self.inner.upper())

    @pymethod()
    def capitalize(self, vm: VirtualMachine) -> PyObjectRef:
        return vm.ctx.new_bytes(self.inner.capitalize())

    @pymethod()
    def swapcase(self, vm: VirtualMachine) -> PyObjectRef:
        return vm.ctx.new_bytes(self.inner.swapcase())

    @pymethod()
    def hex(
        self,
        sep: Optional[PyObjectRef] = None,
        bytes_per_sep: Optional[PyObjectRef] = None,
        *,
        vm: VirtualMachine,
    ) -> PyObjectRef:
        raise NotImplementedError

    @pyclassmethod()
    @staticmethod
    def fromhex(
        class_: PyTypeRef, string: PyObjectRef, *, vm: VirtualMachine
    ) -> PyObjectRef:
        raise NotImplementedError

    # TODO: impl PyBytes @ 115

    # TODO:
    # @pymethod()
    # def center(self, options: ByteInnerPaddingOptions, *, vm: VirtualMachine)

    # TODO: impl PyBytes @ 554
    # TODO: impl Constructor for PyBytes
    # TODO: impl AsMapping for PyBytes @ 580
    # TODO: impl AsSequence for PyBytes @ 586
    # TODO: impl PyBytes @ 595
    # TODO: impl Hashable for PyBytes @ 625
    # TODO: impl Comparable for PyBytes @ 632
    # TODO: impl Iterable for PyBytes @ 657

@po.pyimpl()  # TODO
@po.pyclass("bytes_iterator")
@dataclass
class PyBytesIterator(po.PyClassImpl, po.PyValueMixin):
    internal: PositionIterInternal[PyBytesRef]

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.bytes_iterator_type

    # impl PyBytesIterator @ 679

    # impl IterNextIterable for PyBytesIterator @ 701
    # impl IterNext for PyBytesIterator @ 702


PyBytesRef: TypeAlias = "PyRef[PyBytes]"


def init(context: PyContext) -> None:
    PyBytes.extend_class(context, context.types.bytes_type)
    PyBytesIterator.extend_class(context, context.types.bytes_iterator_type)
