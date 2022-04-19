from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar, Optional, TypeAlias

from common.error import PyImplBase, unreachable
from vm.builtins.slice import SaturatedSlice
from vm.protocol import sequence

if TYPE_CHECKING:
    from vm.builtins.iter import PositionIterInternal
    from vm.builtins.pytype import PyTypeRef
    from vm.pyobject import PyContext
    from vm.builtins.pystr import PyStrRef
    from vm.pyobjectrc import PyRef, PyObjectRef, PyObject
    from vm.vm import VirtualMachine
    from vm.function_ import FuncArgs, ArgBytesLike
    from vm.builtins.int import PyIntRef

from common.deco import pymethod, pyproperty, pyslot, pystaticmethod
import vm.pyobject as po
import vm.pyobjectrc as prc
import vm.types.slot as slot
import vm.sliceable as sliceable
import vm.protocol.mapping as mapping


@po.tp_flags(basetype=True)
@po.pyimpl(
    hashable=False,
    comparable=True,
    as_sequence=True,
    as_mapping=True,
    iterable=True,
)
@po.pyclass("bytearray")
@dataclass
class PyByteArray(
    po.PyClassImpl,
    slot.AsMappingMixin,
    slot.IterableMixin,
    slot.ComparableMixin,
    slot.AsSequenceMixin,
):
    inner: bytearray

    MAPPING_METHODS: ClassVar[mapping.PyMappingMethods] = mapping.PyMappingMethods(
        length=lambda m, vm: PyByteArray.mapping_downcast(m)._._len(),
        subscript=lambda m, needle, vm: PyByteArray.mapping_downcast(m)._._getitem(
            needle, vm
        ),
        ass_subscript=lambda m, needle, value, vm: PyByteArray.ass_subscript(
            PyByteArray.mapping_downcast(m), needle, value, vm
        ),
    )

    SEQUENCE_METHODS: ClassVar[sequence.PySequenceMethods] = sequence.PySequenceMethods(
        length=lambda s, vm: PyByteArray.sequence_downcast(s)._._len(),
        concat=lambda s, other, vm: PyByteArray.sequence_downcast(s)._.concat(
            other, vm
        ),  # TODO
        repeat=lambda s, n, vm: PyByteArray.sequence_downcast(s)._mul(n, vm),  # TODO
        item=lambda s, i, vm: PyByteArray.sequence_downcast(s)._.get_item_by_index(
            vm, i
        ),  # FIXME!
        ass_item=None,  # TODO
        inplace_concat=None,  # TODO
        inplace_repeat=None,  # TODO
    )

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.bytearray_type

    @staticmethod
    def new_ref(data: bytearray, ctx: PyContext) -> PyRef[PyByteArray]:
        return prc.PyRef.new_ref(
            PyByteArray.from_(data), ctx.types.bytearray_type, None
        )

    @classmethod
    def ass_subscript(
        cls,
        zelf: PyRef[PyByteArray],
        needle: PyObjectRef,
        value: Optional[PyObjectRef],
        vm: VirtualMachine,
    ) -> None:
        if value is not None:
            return cls._setitem(zelf, needle, value, vm)
        else:
            zelf._._delitem(needle, vm)

    @classmethod
    def as_mapping(
        cls, zelf: PyRef[PyByteArray], vm: VirtualMachine
    ) -> mapping.PyMappingMethods:
        return cls.MAPPING_METHODS

    def borrow_buf(self) -> bytearray:
        return self.inner

    def borrow_buf_mut(self) -> bytearray:
        return self.inner

    @staticmethod
    def from_(elements: bytearray) -> PyByteArray:
        return PyByteArray(elements)

    @staticmethod
    def default() -> PyByteArray:
        return PyByteArray(bytearray())

    @pyslot
    @staticmethod
    def slot_new(
        class_: PyTypeRef, args: FuncArgs, vm: VirtualMachine
    ) -> PyByteArrayRef:
        return PyByteArray.default().into_pyresult_with_type(vm, class_)

    # TODO
    # @pymethod(True)
    # def i__init__(self, options: ByteInnerNewOptions, vm: VirtualMachine) -> None:
    #     raise NotImplementedError

    @pymethod(True)
    @staticmethod
    def i__repr__(zelf: PyRef[PyByteArray], vm: VirtualMachine) -> PyStrRef:
        return vm.mk_str(repr(zelf._.inner))

    @pymethod(True)
    def i__alloc__(self, vm: VirtualMachine) -> PyIntRef:
        return vm.ctx.new_int(self.inner.__alloc__())

    def _len(self) -> int:
        return len(self.inner)

    @pymethod(True)
    def i__len__(self, vm: VirtualMachine) -> PyIntRef:
        return vm.ctx.new_int(self._len())

    @pymethod(True)
    def i__sizeof__(self, vm: VirtualMachine) -> PyIntRef:
        raise NotImplementedError

    @pymethod(True)
    def i__add__(self, other: ArgBytesLike, vm: VirtualMachine) -> PyRef[PyByteArray]:
        v = other.value.methods.obj_bytes(other.value)
        return PyByteArray(self.inner + v).into_ref(vm)

    @pymethod(True)
    def i__contains__(self, needle: PyObjectRef, vm: VirtualMachine) -> PyIntRef:
        raise NotImplementedError

    @staticmethod
    def _setitem(
        zelf: PyRef[PyByteArray],
        needle: PyObject,
        value: PyObjectRef,
        vm: VirtualMachine,
    ) -> None:
        raise NotImplementedError

    @pymethod(True)
    @classmethod
    def i__setitem__(
        cls,
        zelf: PyRef[PyByteArray],
        needle: PyObjectRef,
        value: PyObjectRef,
        vm: VirtualMachine,
    ) -> None:
        cls._setitem(zelf, needle, value, vm)

    def index_in_bounds(self, i: int) -> bool:
        if i >= 0:
            return i < len(self.inner)
        else:
            return -i <= len(self.inner)

    def get_item_by_index(self, vm: VirtualMachine, i: int) -> int:
        if not self.index_in_bounds(i):
            vm.new_index_error("index out of range")
        return self.inner[i]

    def get_item_by_slice(self, vm: VirtualMachine, slice: SaturatedSlice):
        # TODO: add return type
        raise NotImplementedError

    def _getitem(self, needle: PyObject, vm: VirtualMachine) -> PyObjectRef:
        s = sliceable.SequenceIndex.try_from_borrowed_object(vm, needle)
        if isinstance(s, sliceable.SequenceIndexInt):
            return vm.ctx.new_int(self.get_item_by_index(vm, s.value))
        elif isinstance(s, sliceable.SequenceIndexSlice):
            return PyByteArray.new_ref(self.get_item_by_slice(vm, s.value), vm.ctx)
        unreachable()

    @pymethod(True)
    def i__getitem__(self, needle: PyObjectRef, vm: VirtualMachine) -> PyObjectRef:
        return self._getitem(needle, vm)

    def _delitem(self, needle: PyObject, vm: VirtualMachine) -> None:
        raise NotImplementedError

    @pymethod(True)
    def i__delitem__(self, needle: PyObjectRef, vm: VirtualMachine) -> None:
        self._delitem(needle, vm)

    # @pyproperty()
    # def exports(self) -> int:

    # TODO
    # @pystaticmethod()
    # def maketrans(from_: )

    # TODO impl PyByteArray @ 100

    @classmethod
    def iter(
        cls, zelf: PyRef[PyByteArray], vm: VirtualMachine
    ) -> PyRef[PyByteArrayIterator]:
        return PyByteArrayIterator(PositionIterInternal.new(zelf, 0)).into_object(vm)

    @classmethod
    def cmp(
        cls,
        zelf: PyRef[PyByteArray],
        other: PyObject,
        op: slot.PyComparisonOp,
        vm: VirtualMachine,
    ) -> slot.PyComparisonValue:
        if (res := op.identical_optimization(zelf, other)) is not None:
            return slot.PyComparisonValue(res)
        try:
            res = other.try_bytes_like(vm, lambda value: op.eval_(zelf._.inner, value))
        except PyImplBase as _:
            return slot.PyComparisonValue(None)
        return slot.PyComparisonValue(res)

    @classmethod
    def as_sequence(
        cls, zelf: PyRef[PyByteArray], vm: VirtualMachine
    ) -> sequence.PySequenceMethods:
        return cls.SEQUENCE_METHODS


PyByteArrayRef: TypeAlias = "PyRef[PyByteArray]"


@po.pyimpl(iter_next=True)
@po.pyclass("bytearray_iterator")
@dataclass
class PyByteArrayIterator(po.PyClassImpl):
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
