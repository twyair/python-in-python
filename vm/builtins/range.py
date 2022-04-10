from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vm.builtins.pytype import PyTypeRef
    from vm.pyobject import PyContext
    from vm.builtins.int import PyIntRef
    from vm.vm import VirtualMachine
import vm.pyobject as po


@po.pyimpl(
    as_mapping=True, as_sequence=True, hashable=True, comparable=True, iterable=True
)
@po.pyclass("range")
@dataclass
class PyRange(po.PyClassImpl, po.PyValueMixin):
    start: PyIntRef
    stop: PyIntRef
    step: PyIntRef

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.range_type

    # TODO: impl PyRange @ 83
    # TODO: impl PyRange @ 183
    # TODO: impl PyRange @ 381
    # TODO: impl AsMapping for PyRange
    # TODO: impl AsSequence for PyRange
    # TODO: impl Hashable for PyRange
    # TODO: impl Comparable for PyRange
    # TODO: impl Iterable for PyRange


@po.pyimpl(constructor=True, iter_next=True)
@po.pyclass("longrange_iterator")
@dataclass
class PyLongRangeIterator(po.PyClassImpl, po.PyValueMixin):
    index: int
    start: int
    step: int
    length: int

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.longrange_iterator_type

    # TODO: impl PyLongRangeIterator @ 533
    # TODO: impl Unconstructible for PyLongRangeIterator
    # TODO: impl IterNextIterable for PyLongRangeIterator
    # TODO: impl IterNext for PyLongRangeIterator


@po.pyimpl(constructor=True, iter_next=True)
@po.pyclass("range_iterator")
@dataclass
class PyRangeIterator(po.PyValueMixin, po.PyClassImpl):
    index: int
    start: int
    step: int
    length: int

    # TODO: impl PyRangeIterator @ 598
    # TODO: impl Unconstructible for PyRangeIterator
    # TODO: impl IterNextIterable for PyRangeIterator
    # TODO: impl IterNext for PyRangeIterator


def init(context: PyContext) -> None:
    PyRange.extend_class(context, context.types.range_type)
    PyLongRangeIterator.extend_class(context, context.types.longrange_iterator_type)
    PyRangeIterator.extend_class(context, context.types.range_iterator_type)
