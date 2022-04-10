from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from vm.builtins.pytype import PyTypeRef
    from vm.coroutine import Coro
    from vm.pyobject import (
        PyContext
    )
    from vm.pyobjectrc import PyRef
    from vm.vm import VirtualMachine
import vm.pyobject as po

@po.pyimpl(constructor=True, iter_next=True)
@po.pyclass("coroutine")
@dataclass
class PyCoroutine(po.TryFromObjectMixin, po.PyClassImpl, po.PyValueMixin):
    inner: Coro

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.coroutine_type


@po.pyimpl(iter_next=True)
@po.pyclass("coroutine_wrapper")
@dataclass
class PyCoroutineWrapper(po.PyClassImpl, po.PyValueMixin):
    coro: PyRef[PyCoroutine]

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.coroutine_wrapper_type


def init(ctx: PyContext) -> None:
    PyCoroutine.extend_class(ctx, ctx.types.coroutine_type)
    PyCoroutineWrapper.extend_class(ctx, ctx.types.coroutine_wrapper_type)
