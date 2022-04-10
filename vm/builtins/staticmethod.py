from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from vm.builtins.pytype import PyTypeRef
    from vm.pyobject import PyClassImpl, PyContext, PyValueMixin, pyclass, pyimpl, tp_flags
    from vm.pyobjectrc import PyObjectRef
    from vm.vm import VirtualMachine
import vm.pyobject as po

@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl(callable=True, get_descriptor=True, constructor=True)
@po.pyclass("staticmethod")
@dataclass
class PyStaticMethod(po.PyClassImpl, po.PyValueMixin):
    callable: PyObjectRef

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.staticmethod_type

    # TODO: impl Callable for PyStaticMethod
    # TODO: impl GetDescriptor for PyStaticMethod
    # TODO: impl Constructor for PyStaticMethod
    # TODO: impl PyStaticMethod @ 47
    # TODO: impl PyStaticMethod @ 63


def init(context: PyContext) -> None:
    PyStaticMethod.extend_class(context, context.types.staticmethod_type)
