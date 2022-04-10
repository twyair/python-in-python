from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, Set, Union
if TYPE_CHECKING:
    from vm.builtins.pytype import PyTypeRef
    from vm.pyobject import PyClassImpl, PyContext, PyValueMixin, pyclass, pyimpl
    from vm.pyobjectrc import PyObjectRef, PyRef
    from vm.vm import VirtualMachine
import vm.pyobject as po

@po.pyimpl(hashable=True, comparable=True)
@po.pyclass("slice")
@dataclass
class PySlice(po.PyClassImpl, po.PyValueMixin):
    start: Optional[PyObjectRef]
    stop: PyObjectRef
    step: Optional[PyObjectRef]

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.slice_type

    # TODO: impl PySlice @ 29
    # TODO: impl Comparable for PySlice
    # TODO: impl Unhashable for PySlice


@po.pyimpl()
@po.pyclass("EllipsisType")
@dataclass
class PyEllipsis(po.PyClassImpl, po.PyValueMixin):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.ellipsis_type

    # TODO: impl Constructor for PyEllipsis
    # TODO: impl PyEllipsis @ 440


def init(context: PyContext) -> None:
    PySlice.extend_class(context, context.types.slice_type)
    PyEllipsis.extend_class(context, context.ellipsis.clone_class())
