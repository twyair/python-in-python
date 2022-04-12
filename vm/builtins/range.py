from __future__ import annotations
from abc import ABC
from dataclasses import dataclass
import enum
from typing import TYPE_CHECKING, ClassVar, Optional


if TYPE_CHECKING:
    from vm.function_ import FuncArgs
    from vm.builtins.pytype import PyTypeRef
    from vm.pyobject import PyContext
    from vm.pyobjectrc import PyRef, PyObjectRef, PyObject
    from vm.builtins.int import PyIntRef
    from vm.vm import VirtualMachine
    from vm.protocol.mapping import PyMappingMethods
    from vm.protocol.sequence import PySequenceMethods

import vm.pyobject as po
import vm.types.slot as slot
import vm.builtins.int as pyint
import vm.builtins.slice as pyslice
import vm.protocol.iter as iter_
import vm.protocol.mapping as mapping
import vm.protocol.sequence as sequence
from common import is_isize
from common.error import PyImplBase, unreachable
from common.hash import PyHash, hash_iter
from common.deco import pymethod, pyproperty, pyslot


class SearchType(enum.Enum):
    Count = enum.auto()
    Contains = enum.auto()
    Index = enum.auto()


def iter_search(
    obj: PyObjectRef, item: PyObjectRef, flag: SearchType, vm: VirtualMachine
) -> int:
    count = 0
    iter_ = obj.get_iter(vm)
    for element in iter_.iter_without_hint(vm):
        if vm.bool_eq(item, element):
            if flag == SearchType.Index:
                return count
            elif flag == SearchType.Contains:
                return 1
            else:
                count += 1
    if flag == SearchType.Count:
        return count
    elif flag == SearchType.Contains:
        return 0
    elif flag == SearchType.Index:
        # TODO
        vm.new_value_error("{} not in range".format(item.repr(vm)))


@po.pyimpl(
    as_mapping=True, as_sequence=True, hashable=True, comparable=True, iterable=True
)
@po.pyclass("range")
@dataclass
class PyRange(
    po.PyClassImpl,
    po.PyValueMixin,
    po.TryFromObjectMixin,
    slot.AsMappingMixin,
    slot.AsSequenceMixin,
    slot.HashableMixin,
    slot.ComparableMixin,
    slot.IterableMixin,
):
    start: PyIntRef
    stop: PyIntRef
    step: PyIntRef

    MAPPING_METHODS: ClassVar[mapping.PyMappingMethods] = mapping.PyMappingMethods(
        length=lambda m, vm: PyRange.mapping_downcast(m)._.len(),
        subscript=lambda m, needle, vm: PyRange.mapping_downcast(m)._._getitem(
            needle, vm
        ),
    )

    SEQUENCE_METHODS: ClassVar[sequence.PySequenceMethods] = sequence.PySequenceMethods(
        length=lambda s, vm: PyRange.sequence_downcast(s)._.len(),
        item=lambda s, i, vm: PyRange.sequence_downcast(s)._.protocol_item(i, vm),
        contains=lambda s, needle, vm: PyRange.sequence_downcast(s)._._contains(
            needle, vm
        ),
    )

    def protocol_item(self, i: int, vm: VirtualMachine) -> PyObjectRef:
        item = self.get(i)
        if item is not None:
            return pyint.PyInt.from_(item).into_ref(vm)
        else:
            vm.new_index_error("index out of range")

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.range_type

    def offset(self, value: int) -> Optional[int]:
        start = self.start._.as_int()
        stop = self.stop._.as_int()
        step = self.step._.as_int()
        if step > 0 and value >= start and value < stop:
            return value - start
        elif step < 0 and value <= start and value > stop:
            return start - value
        else:
            return None

    def index_of(self, value: int) -> Optional[int]:
        step = self.step._.as_int()
        if (offset := self.offset(value)) is not None and offset % step == 0:
            return abs(offset // step)
        else:
            return None

    def is_empty(self) -> bool:
        return self.compute_length() == 0

    def forward(self) -> bool:
        return self.start._.as_int() < self.stop._.as_int()

    def get(self, index: int) -> Optional[int]:
        if self.is_empty():
            return None

        start = self.start._.as_int()
        stop = self.stop._.as_int()
        step = self.step._.as_int()
        if index < 0:
            length = self.compute_length()
            index += length
            if index < 0:
                return None
            else:
                return start + step * index
        else:
            index = start + step * index

            if step > 0 and stop > index or step < 0 and stop < index:
                return index
            else:
                return None

    def compute_length(self) -> int:
        start = self.start._.as_int()
        step = self.step._.as_int()
        stop = self.stop._.as_int()

        if step > 0 and start < stop:
            if step == 1:
                return stop - start
            else:
                return (stop - start - 1) // step + 1
        elif step < 0 and start > stop:
            return -(start - stop - 1) // step + 1
        else:
            return 0

    def len(self) -> int:
        return self.compute_length()

    def _getitem(self, subscript: PyObjectRef, vm: VirtualMachine) -> PyObjectRef:
        idx = RangeIndex.try_from_object(vm, subscript)
        if isinstance(idx, RangeIndexSlice):
            substart, substop, substep = idx.value._.inner_indices(
                self.compute_length(), vm
            )
            range_step = self.step._.as_int()
            range_start = self.start._.as_int()
            substep *= range_step
            substart = (substart * range_step) + range_start
            substop = (substop * range_step) + range_start
            return PyRange(
                start=vm.ctx.new_int(substart),
                stop=vm.ctx.new_int(substop),
                step=vm.ctx.new_int(substep),
            ).into_ref(vm)
        elif isinstance(idx, RangeIndexInt):
            if (value := self.get(idx.value._.as_int())) is not None:
                return vm.ctx.new_int(value)
            else:
                vm.new_index_error("range object index out of range")
        unreachable()

    def _contains(self, needle: PyObjectRef, vm: VirtualMachine) -> bool:
        if (i := needle.payload_if_exact(pyint.PyInt, vm)) is not None:
            if (offset := self.offset(i.as_int())) is not None:
                return offset % (self.step._.as_int()) == 0  # FIXME?
            else:
                return False
        else:
            i = iter_search(self.into_ref(vm), needle, SearchType.Contains, vm)
            if i is None:
                return False
            else:
                return i != 0

    @pyproperty()
    def get_start(self, vm: VirtualMachine) -> PyIntRef:
        return self.start

    @pyproperty()
    def get_stop(self, vm: VirtualMachine) -> PyIntRef:
        return self.stop

    @pyproperty()
    def get_step(self, vm: VirtualMachine) -> PyIntRef:
        return self.step

    @pymethod()
    def i__reversed__(self, vm: VirtualMachine) -> PyObjectRef:
        start = self.start._.as_int()
        step = self.step._.as_int()

        length = self.len()
        new_stop = start - step
        start = new_stop + length * step
        step = -step

        if is_isize(start) and is_isize(step) and is_isize(new_stop):
            return PyRangeIterator(
                index=0, start=start, step=step, length=length
            ).into_ref(vm)
        else:
            return PyLongRangeIterator(
                index=0, start=start, step=step, length=length
            ).into_ref(vm)

    @pymethod()
    def i__len__(self, vm: VirtualMachine) -> PyObjectRef:
        return pyint.PyInt.from_(self.len()).into_ref(vm)

    @pymethod()
    def i__bool__(self, vm: VirtualMachine) -> PyObjectRef:
        return vm.ctx.new_bool(not self.is_empty())

    @pymethod()
    def i__contains__(self, needle: PyObjectRef, vm: VirtualMachine) -> PyObjectRef:
        return vm.ctx.new_bool(self._contains(needle, vm))

    @pymethod()
    def i__reduce__(self, vm: VirtualMachine) -> PyObjectRef:
        range_parameters = vm.ctx.new_tuple([self.start, self.stop, self.step])
        return vm.ctx.new_tuple([vm.ctx.types.range_type, range_parameters])

    @pymethod()
    def index(self, needle: PyObjectRef, vm: VirtualMachine) -> PyObjectRef:
        try:
            i = needle.downcast(pyint.PyInt)
        except PyImplBase as _:
            pass
        else:
            if (idx := self.index_of(i._.as_int())) is not None:
                return vm.ctx.new_int(idx)
            else:
                vm.new_value_error(f"{i} is not in range")

        return vm.ctx.new_int(
            iter_search(self.into_ref(vm), needle, SearchType.Index, vm)
        )

    @pymethod()
    def count(self, item: PyObjectRef, vm: VirtualMachine) -> PyIntRef:
        try:
            i = item.downcast(pyint.PyInt)
        except PyImplBase as _:
            pass
        else:
            if self.index_of(i._.as_int()) is not None:
                return vm.ctx.new_int(1)
            else:
                return vm.ctx.new_int(0)

        return vm.ctx.new_int(
            iter_search(self.into_ref(vm), item, SearchType.Count, vm)
        )

    @pymethod()
    def i__getitem__(self, subscript: PyObjectRef, vm: VirtualMachine) -> PyObjectRef:
        return self._getitem(subscript, vm)

    @pyslot()
    @staticmethod
    def slot_new(class_: PyTypeRef, args: FuncArgs, vm: VirtualMachine) -> PyObjectRef:
        raise NotImplementedError

    @classmethod
    def as_mapping(cls, zelf: PyRef[PyRange], vm: VirtualMachine) -> PyMappingMethods:
        return cls.MAPPING_METHODS

    @classmethod
    def as_sequence(cls, zelf: PyRef[PyRange], vm: VirtualMachine) -> PySequenceMethods:
        return cls.SEQUENCE_METHODS

    @classmethod
    def hash(cls, zelf: PyRef[PyRange], vm: VirtualMachine) -> PyHash:
        length = zelf._.compute_length()
        elements = [vm.ctx.new_int(length), vm.ctx.get_none(), vm.ctx.get_none()]
        if length != 0:
            elements[1] = zelf._.start
            if length != 1:
                elements[2] = zelf._.step
        return hash_iter(elements, vm)

    @classmethod
    def iter(cls, zelf: PyRef[PyRange], vm: VirtualMachine) -> PyObjectRef:
        start = zelf._.start._.as_int()
        step = zelf._.step._.as_int()
        stop = zelf._.stop._.as_int()
        length = zelf._.len()
        if is_isize(start) and is_isize(step) and is_isize(stop):
            return PyRangeIterator(
                index=0, start=start, step=step, length=length
            ).into_ref(vm)
        else:
            return PyLongRangeIterator(
                index=0, start=start, step=step, length=length
            ).into_ref(vm)

    @classmethod
    def cmp(
        cls,
        zelf: PyRef[PyRange],
        other: PyObject,
        op: slot.PyComparisonOp,
        vm: VirtualMachine,
    ) -> po.PyComparisonValue:
        def do() -> po.PyComparisonValue:
            if zelf.is_(other):
                return po.PyComparisonValue(True)
            rhs = other.downcast_ref(PyRange)
            if rhs is None:
                return po.PyComparisonValue(None)
            lhs_len = zelf._.compute_length()
            return po.PyComparisonValue(
                lhs_len == rhs._.compute_length()
                and (
                    lhs_len == 0
                    or zelf._.start._.as_int() != rhs._.start._.as_int()
                    and zelf._.step._.as_int() == rhs._.step._.as_int()
                )
            )

        return op.eq_only(do)


@dataclass
class RangeIndex(ABC):
    @staticmethod
    def try_from_object(
        vm: VirtualMachine, obj: PyObjectRef
    ) -> RangeIndexInt | RangeIndexSlice:
        raise NotImplementedError


@dataclass
class RangeIndexInt(RangeIndex):
    value: PyIntRef


@dataclass
class RangeIndexSlice(RangeIndex):
    value: PyRef[pyslice.PySlice]


@po.pyimpl(constructor=False, iter_next=True)
@po.pyclass("longrange_iterator")
@dataclass
class PyLongRangeIterator(
    po.PyClassImpl,
    po.PyValueMixin,
    po.TryFromObjectMixin,
    slot.IterNextMixin,
    slot.IterNextIterableMixin,
):
    index: int
    start: int
    step: int
    length: int

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.longrange_iterator_type

    # TODO: impl PyLongRangeIterator @ 533

    @classmethod
    def next(
        cls, zelf: PyRef[PyLongRangeIterator], vm: VirtualMachine
    ) -> iter_.PyIterReturn:
        index = zelf._.index
        zelf._.index += 1
        if index < zelf._.length:
            return iter_.PyIterReturnReturn(
                vm.ctx.new_int(zelf._.start + index * zelf._.step)
            )
        else:
            return iter_.PyIterReturnStopIteration(None)


@po.pyimpl(constructor=False, iter_next=True)
@po.pyclass("range_iterator")
@dataclass
class PyRangeIterator(
    po.PyValueMixin,
    po.PyClassImpl,
    po.TryFromObjectMixin,
    slot.IterNextMixin,
    slot.IterNextIterableMixin,
):
    index: int
    start: int
    step: int
    length: int

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.range_iterator_type

    # TODO: impl PyRangeIterator @ 598

    @classmethod
    def next(
        cls, zelf: PyRef[PyRangeIterator], vm: VirtualMachine
    ) -> iter_.PyIterReturn:
        index = zelf._.index
        zelf._.index += 1
        if index < zelf._.length:
            return iter_.PyIterReturnReturn(
                vm.ctx.new_int(zelf._.start + index * zelf._.step)
            )
        else:
            return iter_.PyIterReturnStopIteration(None)


def init(context: PyContext) -> None:
    PyRange.extend_class(context, context.types.range_type)
    PyLongRangeIterator.extend_class(context, context.types.longrange_iterator_type)
    PyRangeIterator.extend_class(context, context.types.range_iterator_type)
