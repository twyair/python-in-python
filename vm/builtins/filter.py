from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from vm.builtins.pytype import PyTypeRef
    from vm.pyobject import PyContext
    from vm.pyobjectrc import PyObjectRef
    from protocol.iter import PyIter
    from vm.vm import VirtualMachine
import vm.pyobject as po

@po.tp_flags(basetype=True)
@po.pyimpl(iter_next=True, constructor=True)
@po.pyclass("filter")
@dataclass
class PyFilter(po.PyValueMixin, po.PyClassImpl):
    predicate: PyObjectRef
    iterator: PyIter

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.filter_type

    # TODO: impl Constructor for PyFilter

    # TODO: impl IterNextIterable for PyFilter
    # TODO: impl IterNext for PyFilter


def init(context: PyContext) -> None:
    PyFilter.extend_class(context, context.types.filter_type)
