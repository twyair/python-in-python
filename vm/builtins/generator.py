from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vm.builtins.pystr import PyStrRef
    from vm.builtins.pytype import PyTypeRef
    from vm.coroutine import Coro
    from vm.frame import FrameRef
    from vm.pyobject import PyContext
    from vm.vm import VirtualMachine
import vm.pyobject as po

@po.pyimpl(constructor=True, iter_next=True)
@po.pyclass("generator")
@dataclass
class PyGenerator(po.PyValueMixin, po.PyClassImpl):
    inner: Coro

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.generator_type

    def as_coro(self) -> Coro:
        return self.inner

    @staticmethod
    def new(frame: FrameRef, name: PyStrRef) -> PyGenerator:
        return PyGenerator(Coro.new(frame, name))

    # TODO: impl PyGenerator @ 28

    # TODO: impl IterNextIterable for PyGenerator
    # TODO: impl IterNext for PyGenerator


def init(ctx: PyContext) -> None:
    return PyGenerator.extend_class(ctx, ctx.types.generator_type)
