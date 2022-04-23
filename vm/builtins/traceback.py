from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, TypeAlias

if TYPE_CHECKING:
    from vm.builtins.pytype import PyTypeRef
    from vm.pyobject import PyContext
    from vm.pyobjectrc import PyRef
    from vm.frame import FrameRef
    from vm.vm import VirtualMachine
import vm.pyobject as po


@po.pyimpl()
@po.pyclass("traceback")
@dataclass
class PyTraceback(po.PyClassImpl):
    next: Optional[PyTracebackRef]
    frame: FrameRef
    lasti: int
    lineno: int

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.traceback_type

    # TODO: impl PyTraceback @ 22

    @staticmethod
    def new(
        next: Optional[PyRef[PyTraceback]], frame: FrameRef, lasti: int, lineno: int
    ) -> PyTraceback:
        return PyTraceback(next=next, frame=frame, lasti=lasti, lineno=lineno)


PyTracebackRef: TypeAlias = "PyRef[PyTraceback]"


def init(context: PyContext) -> None:
    PyTraceback.extend_class(context, context.types.traceback_type)
