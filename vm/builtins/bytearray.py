from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar, TypeAlias

if TYPE_CHECKING:
    from vm.builtins.iter import PositionIterInternal
    from vm.builtins.pytype import PyTypeRef
    from vm.bytesinner import PyBytesInner
    from vm.pyobject import PyContext

    from vm.pyobjectrc import PyRef
    from vm.vm import VirtualMachine
import vm.pyobject as po


@po.tp_flags(basetype=True)
@po.pyimpl(comparable=True, as_sequence=True, as_mapping=True, iterable=True)
@po.pyclass("bytearray")
@dataclass
class PyByteArray(po.PyClassImpl, po.PyValueMixin):
    inner: PyBytesInner
    exports: int

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.bytearray_type

    @staticmethod
    def new_ref(data: bytearray, ctx: PyContext) -> PyRef[PyByteArray]:
        return PyRef.new_ref(PyByteArray.from_(data), ctx.types.bytearray_type, None)

    @staticmethod
    def from_inner(inner: PyBytesInner) -> PyByteArray:
        return PyByteArray(inner=inner, exports=0)

    def borrow_buf(self) -> bytearray:
        return self.inner.elements

    def borrow_buf_mut(self) -> bytearray:
        return self.inner.elements

    @staticmethod
    def from_(elements: bytearray) -> PyByteArray:
        return PyByteArray(PyBytesInner(elements), 0)

    # TODO impl PyByteArray @ 100
    # TODO: impl PyByteArray @ 695
    # TODO: impl Comparable for PyByteArray @ 712
    # TODO: impl AsMapping for PyByteArray @ 767
    # TODO: impl AsSequence for PyByteArray @ 773
    # TODO: impl Iterable for PyByteArray @ 828


PyByteArrayRef: TypeAlias = "PyRef[PyByteArray]"


@po.pyimpl(iter_next=True)
@po.pyclass("bytearray_iterator")
@dataclass
class PyByteArrayIterator(po.PyClassImpl, po.PyValueMixin):
    internal: PositionIterInternal[PyByteArrayRef]

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.bytearray_iterator_type

    # TODO: impl PyByteArrayIterator @ 854
    # TODO: impl IterNextIterable for PyByteArrayIterator
    # TODO: impl IterNext for PyByteArrayIterator


def init(context: PyContext) -> None:
    PyByteArray.extend_class(context, context.types.bytearray_type)
    PyByteArrayIterator.extend_class(context, context.types.bytearray_iterator_type)
