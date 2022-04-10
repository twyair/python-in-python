from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Set, TypeAlias

if TYPE_CHECKING:
    from vm.builtins.pytype import PyTypeRef
    from vm.pyobject import PyContext
    from vm.pyobjectrc import PyObjectRef, PyRef
    from vm.vm import VirtualMachine
import vm.pyobject as po


@po.tp_flags(basetype=True)
@po.pyimpl(as_sequence=True, hashable=True, comparable=True, iterable=True)
@po.pyclass("set")
@dataclass
class PySet(po.PyClassImpl, po.PyValueMixin, po.TryFromObjectMixin):
    inner: PySetInner

    @staticmethod
    def new_ref(ctx: PyContext) -> PyRef[PySet]:
        return PyRef.new_ref(PySet.default(), ctx.types.set_type, None)

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.set_type

    @staticmethod
    def default() -> PySet:
        raise NotImplementedError

    def elements(self) -> list[PyObjectRef]:
        return self.inner.elements()

    # TODO: impl PySet @ 397
    # TODO: impl AsSequence for PySet
    # TODO: impl Comparable for PySet
    # TODO: impl Iterable for PySet


@po.tp_flags(basetype=True)
@po.pyimpl(
    as_sequence=True, hashable=True, comparable=True, iterable=True, constructor=True
)
@po.pyclass("frozenset")
@dataclass
class PyFrozenSet(po.PyClassImpl, po.PyValueMixin):
    inner: PySetInner

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.frozenset_type

    @staticmethod
    def default() -> PyFrozenSet:
        return PyFrozenSet(PySetInner.default())

    def elements(self) -> list[PyObjectRef]:
        return self.inner.elements()

    # TODO: impl Constructor for PyFrozenSet
    # TODO: impl PyFrozenSet @ 724
    # TODO: impl AsSequence for PyFrozenSet
    # TODO: impl Hashable for PyFrozenSet
    # TODO: impl Comparable for PyFrozenSet
    # TODO: impl Iterable for PyFrozenSet


@dataclass
class PySetInner:
    content: SetContentType

    @staticmethod
    def default() -> PySetInner:
        return PySetInner(set())

    def elements(self) -> list[PyObjectRef]:
        return list(self.content)

    # TODO: impl PySetInner


# FIXME
SetContentType: TypeAlias = "Set[PyObjectRef]"


@po.pyimpl(constructor=True, iter_next=True)
@po.pyclass("set_iterator")
@dataclass
class PySetIterator(po.PyClassImpl, po.PyValueMixin):
    # TODO: add fields
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.set_iterator_type

    # TODO: impl PySetIterator @ 969
    # TODO: impl Unconstructible for PySetIterator
    # TODO: impl IterNextIterable for PySetIterator
    # TODO: impl IterNext for PySetIterator


def init(context: PyContext) -> None:
    PySet.extend_class(context, context.types.set_type)
    PyFrozenSet.extend_class(context, context.types.frozenset_type)
    PySetIterator.extend_class(context, context.types.set_iterator_type)
