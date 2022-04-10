from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from protocol.iter import PyIter
    from vm.builtins.iter import PositionIterInternal
    from vm.builtins.pytype import PyTypeRef
    from vm.pyobject import PyContext
    from vm.pyobjectrc import PyObjectRef
    from vm.vm import VirtualMachine
import vm.pyobject as po


@po.tp_flags(basetype=True)
@po.pyimpl(iter_next=True, constructor=True)
@po.pyclass("enumerate")
@dataclass
class PyEnumerate(po.PyValueMixin, po.PyClassImpl):
    counter: int
    iterator: PyIter

    # TODO: impl PyEnumerate @ 50
    # TODO: impl Constructor for PyEnumerate

    # TODO: impl IterNextIterable for PyEnumerate
    # TODO: impl IterNext for PyEnumerate


@po.pyimpl(iter_next=True)
@po.pyclass("reversed")
@dataclass
class PyReverseSequenceIterator(po.PyValueMixin, po.PyClassImpl):
    internal: PositionIterInternal[PyObjectRef]

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.reverse_iter_type

    # TODO: impl PyReverseSequenceIterator @ 91
    # TODO: impl IterNextIterable for PyReverseSequenceIterator
    # TODO: impl IterNext for PyReverseSequenceIterator


def init(context: PyContext) -> None:
    PyEnumerate.extend_class(context, context.types.enumerate_type)
    PyReverseSequenceIterator.extend_class(context, context.types.reverse_iter_type)
