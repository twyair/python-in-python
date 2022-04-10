from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from vm.builtins.pytype import PyTypeRef
    from vm.pyobject import PyClassImpl, PyContext, PyValueMixin, pyclass, pyimpl, tp_flags
    from vm.pyobjectrc import PyObjectRef
    from protocol.iter import PyIter
    from vm.vm import VirtualMachine
import vm.pyobject as po

@po.tp_flags(basetype=True)
@po.pyimpl(constructor=True, iter_next=True)
@po.pyclass("map")
@dataclass
class PyMap(po.PyClassImpl, po.PyValueMixin):
    mapper: PyObjectRef
    iterators: list[PyIter]

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.map_type

    # TODO: impl Constructor for PyMap
    # TODO: impl IterNextIterable for PyMap
    # TODO: impl IterNext for PyMap


def init(context: PyContext) -> None:
    PyMap.extend_class(context, context.types.map_type)
