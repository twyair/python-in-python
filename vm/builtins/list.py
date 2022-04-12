from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, TypeAlias

if TYPE_CHECKING:
    from vm.builtins.pytype import PyTypeRef
    from vm.pyobject import PyContext
    from vm.pyobjectrc import PyObjectRef, PyRef
    from vm.builtins.iter import PositionIterInternal
    from vm.vm import VirtualMachine
import vm.pyobject as po
import vm.pyobjectrc as prc


@po.tp_flags(basetype=True)
@po.pyimpl(
    as_mapping=True, iterable=True, hashable=False, comparable=True, as_sequence=True
)
@po.pyclass("list")
@dataclass
class PyList(po.PyClassImpl, po.PyValueMixin, po.TryFromObjectMixin):
    elements: list[PyObjectRef]

    @staticmethod
    def new_ref(value: list[PyObjectRef], ctx: PyContext) -> PyListRef:
        return prc.PyRef.new_ref(PyList(value), ctx.types.list_type, None)

    @staticmethod
    def class_(vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.list_type

    # TODO: impl PyList @ 96
    # TODO: impl AsMapping for PyList
    # TODO: impl AsSequence for PyList
    # TODO: impl Iterable for PyList
    # TODO: impl Comparable for PyList


PyListRef: TypeAlias = "PyRef[PyList]"


@po.pyimpl(constructor=False, iter_next=True)
@po.pyclass("list_iterator")
@dataclass
class PyListIterator(po.PyClassImpl, po.PyValueMixin):
    internal: PositionIterInternal[PyListRef]

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.list_iterator_type

    # TODO: impl PyListIterator @ 519
    # TODO: impl IterNextIterable for PyListIterator
    # TODO: impl IterNext for PyListIterator


@po.pyimpl(constructor=False, iter_next=True)
@po.pyclass("list_reverse_iterator")
@dataclass
class PyListReverseIterator(po.PyClassImpl, po.PyValueMixin):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.list_reverseiterator_type

    # TODO: impl PyListReverseIterator @ 564
    # TODO: impl IterNextIterable for PyListReverseIterator
    # TODO: impl IterNext for PyListReverseIterator


def init(context: PyContext) -> None:
    PyList.extend_class(context, context.types.list_type)
    PyListIterator.extend_class(context, context.types.list_iterator_type)
    PyListReverseIterator.extend_class(context, context.types.list_reverseiterator_type)
