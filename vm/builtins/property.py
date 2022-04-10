from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional
if TYPE_CHECKING:
    from vm.builtins.pytype import PyTypeRef
    from vm.pyobject import PyClassImpl, PyContext, PyValueMixin, pyclass, pyimpl, tp_flags
    from vm.pyobjectrc import PyObjectRef, PyRef
    from vm.vm import VirtualMachine
import vm.pyobject as po

@po.tp_flags(basetype=True)
@po.pyimpl(get_descriptor=True)
@po.pyclass("property")
@dataclass
class PyProperty(po.PyClassImpl, po.PyValueMixin):
    getter: Optional[PyObjectRef]
    setter: Optional[PyObjectRef]
    deleter: Optional[PyObjectRef]
    doc: Optional[PyObjectRef]

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.property_type

    # TODO: impl GetDescriptor for PyProperty


def init(context: PyContext) -> None:
    PyProperty.extend_class(context, context.types.property_type)
    # TODO: extend_class!(context, &context.types.property_type, {
