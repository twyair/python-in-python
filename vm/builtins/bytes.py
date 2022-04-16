from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, TypeAlias
from common.deco import pyclassmethod, pymethod, pystaticmethod

if TYPE_CHECKING:
    from vm.builtins.iter import PositionIterInternal
    from vm.builtins.pytype import PyTypeRef
    from vm.pyobject import PyContext
    from vm.pyobjectrc import PyObject, PyObjectRef, PyRef
    from vm.vm import VirtualMachine
    from vm.sliceable import SequenceIndex

import vm.pyobject as po
import vm.pyobjectrc as prc
import vm.function_ as vm_function_


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
class PyBytes(po.PyClassImpl, po.PyValueMixin, po.TryFromObjectMixin):
    inner: bytes

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.bytes_type

    @staticmethod
    def new_ref(value: bytes, ctx: PyContext) -> PyBytesRef:
        return prc.PyRef.new_ref(PyBytes(value), ctx.types.tuple_type, None)

    @pymethod(True)
    def i__repr__(self, *, vm: VirtualMachine) -> PyObjectRef:
        return vm.mk_str(repr(self.inner))

    @pymethod(True)
    def i__len__(self, *, vm: VirtualMachine) -> PyObjectRef:
        return vm.ctx.new_int(len(self.inner))

    # @pymethod(True)
    # def bytes()

    @pymethod(True)
    def i__sizeof__(self, *, vm: VirtualMachine) -> PyObjectRef:
        return vm.ctx.new_int(self.__sizeof__())

    @pymethod(True)
    def i__add__(self, other: PyObjectRef, *, vm: VirtualMachine) -> PyObjectRef:
        arg = vm_function_.ArgBytesLike.try_from_borrowed_object(vm, other)
        return vm.ctx.new_bytes(self.inner + arg.value.methods.obj_bytes(arg.value))

    @pymethod(True)
    def i__contains__(self, needle: PyObjectRef, vm) -> PyObjectRef:
        raise NotImplementedError

    @pystaticmethod(True)
    @staticmethod
    def maketrans(frm: PyObjectRef, to: PyObjectRef, vm: VirtualMachine) -> PyObjectRef:
        raise NotImplementedError

    def _getitem(self, needle: PyObject, vm: VirtualMachine) -> SequenceIndex:
        raise NotImplementedError

    @pymethod(True)
    def i__getitem__(self, needle: PyObjectRef, vm: VirtualMachine) -> PyObjectRef:
        # FIXME
        return self._getitem(needle, vm)

    @pymethod(True)
    def isalnum(self, vm: VirtualMachine) -> PyObjectRef:
        return vm.ctx.new_bool(self.inner.isalnum())

    @pymethod(True)
    def isalpha(self, vm: VirtualMachine) -> PyObjectRef:
        return vm.ctx.new_bool(self.inner.isalpha())

    @pymethod(True)
    def isascii(self, vm: VirtualMachine) -> PyObjectRef:
        return vm.ctx.new_bool(self.inner.isascii())

    @pymethod(True)
    def isdigit(self, vm: VirtualMachine) -> PyObjectRef:
        return vm.ctx.new_bool(self.inner.isdigit())

    @pymethod(True)
    def islower(self, vm: VirtualMachine) -> PyObjectRef:
        return vm.ctx.new_bool(self.inner.islower())

    @pymethod(True)
    def isspace(self, vm: VirtualMachine) -> PyObjectRef:
        return vm.ctx.new_bool(self.inner.isspace())

    @pymethod(True)
    def isupper(self, vm: VirtualMachine) -> PyObjectRef:
        return vm.ctx.new_bool(self.inner.isupper())

    @pymethod(True)
    def istitle(self, vm: VirtualMachine) -> PyObjectRef:
        return vm.ctx.new_bool(self.inner.istitle())

    @pymethod(True)
    def lower(self, vm: VirtualMachine) -> PyObjectRef:
        return vm.ctx.new_bytes(self.inner.lower())

    @pymethod(True)
    def upper(self, vm: VirtualMachine) -> PyObjectRef:
        return vm.ctx.new_bytes(self.inner.upper())

    @pymethod(True)
    def capitalize(self, vm: VirtualMachine) -> PyObjectRef:
        return vm.ctx.new_bytes(self.inner.capitalize())

    @pymethod(True)
    def swapcase(self, vm: VirtualMachine) -> PyObjectRef:
        return vm.ctx.new_bytes(self.inner.swapcase())

    @pymethod(True)
    def hex(
        self,
        sep: Optional[PyObjectRef] = None,
        bytes_per_sep: Optional[PyObjectRef] = None,
        *,
        vm: VirtualMachine,
    ) -> PyObjectRef:
        raise NotImplementedError

    @pyclassmethod(True)
    @staticmethod
    def fromhex(
        class_: PyTypeRef, string: PyObjectRef, *, vm: VirtualMachine
    ) -> PyObjectRef:
        raise NotImplementedError

    # TODO: impl PyBytes @ 115

    # TODO:
    # @pymethod(True)
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
