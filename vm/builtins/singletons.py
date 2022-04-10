from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from vm.pyobject import PyClassImpl, PyContext, PyValueMixin, pyclass, pyimpl
    from vm.vm import VirtualMachine
    from vm.builtins.pytype import PyTypeRef
import vm.pyobject as po

@po.pyimpl(constructor=True)
@po.pyclass("NoneType")
@dataclass
class PyNone(po.PyClassImpl, po.PyValueMixin):
    @staticmethod
    def class_(vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.none_type

    # TODO: impl Constructor for PyNone
    # TODO: impl PyNone @ 43


@po.pyimpl(constructor=True)
@po.pyclass("NotImplementedType")
@dataclass
class PyNotImplemented(po.PyClassImpl, po.PyValueMixin):
    @staticmethod
    def class_(vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.not_implemented_type

    # TODO: impl Constructor for PyNotImplemented
    # TODO: impl PyNotImplemented @ 74


def init(context: PyContext) -> None:
    PyNone.extend_class(context, context.none.clone_class())
    PyNotImplemented.extend_class(context, context.not_implemented.clone_class())
