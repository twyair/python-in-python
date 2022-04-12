from __future__ import annotations
from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Generic,
    Optional,
    Set,
    Type,
    TypeAlias,
    TypeVar,
    Union,
)

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
    as_mapping=True,
    as_sequence=True,
    hashable=True,
    comparable=True,
    iterable=True,
    constructor=True,
)
@po.pyclass("tuple")
@dataclass
class PyTuple(po.PyClassImpl, po.PyValueMixin, po.TryFromObjectMixin):
    elements: list[PyObjectRef]

    def is_empty(self) -> bool:
        return not self.elements

    def as_slice(self) -> list[PyObjectRef]:
        return self.elements

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.tuple_type

    @staticmethod
    def new_ref(elements: list[PyObjectRef], ctx: PyContext) -> PyTupleRef:
        if not elements:
            return ctx.empty_tuple
        else:
            return prc.PyRef.new_ref(PyTuple(elements), ctx.types.tuple_type, None)

    def intro_ref(self: PyTuple, vm: VirtualMachine) -> PyTupleRef:
        return prc.PyRef.new_ref(self, vm.ctx.types.tuple_type, None)

    def len(self) -> int:
        return len(self.elements)

    def __len__(self) -> int:
        return self.len()

    def fast_getitem(self, i: int) -> PyObjectRef:
        return self.elements[i]

    # TODO: impl Constructor for PyTuple
    # TODO: impl PyTuple @ 149
    # TODO: impl AsMapping for PyTuple
    # TODO: impl AsSequence for PyTuple
    # TODO: impl Hashable for PyTuple
    # TODO: impl Comparable for PyTuple
    # TODO: impl Iterable for PyTuple


PyTupleRef: TypeAlias = "PyRef[PyTuple]"


@po.pyimpl(constructor=True, iter_next=True)
@po.pyclass("tuple_iterator")
@dataclass
class PyTupleIterator(po.PyClassImpl, po.PyValueMixin):
    internal: PositionIterInternal[PyTupleRef]

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.tuple_iterator_type

    # TODO: impl PyTupleIterator @ 417
    # TODO: impl Unconstructible for PyTupleIterator
    # TODO: impl IterNextIterable for PyTupleIterator
    # TODO: impl IterNext for PyTupleIterator


T = TypeVar("T")


@dataclass
class PyTupleTyped(Generic[T]):
    tuple: PyTupleRef

    @staticmethod
    def try_from_object(t: Type[T], obj: PyObjectRef) -> PyTupleTyped[PyRef[T]]:
        raise NotImplementedError

    def __len__(self) -> int:
        return len(self.tuple._.elements)

    def is_empty(self) -> bool:
        return self.tuple._.is_empty()

    def as_slice(self) -> list[T]:
        return self.tuple._.elements  # type: ignore

    def into_pyobject(self, vm: VirtualMachine) -> PyObjectRef:
        return self.tuple


def init(context: PyContext) -> None:
    PyTuple.extend_class(context, context.types.tuple_type)
    PyTupleIterator.extend_class(context, context.types.tuple_iterator_type)
