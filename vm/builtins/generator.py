from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional


if TYPE_CHECKING:
    from vm.builtins.pystr import PyStrRef
    from vm.builtins.pytype import PyTypeRef
    from vm.coroutine import Coro
    from vm.frame import FrameRef
    from vm.pyobject import PyContext
    from vm.pyobjectrc import PyRef, PyObjectRef
    from vm.vm import VirtualMachine
    from vm.builtins.code import PyCode
    from vm.protocol.iter import PyIterReturn

import vm.pyobject as po
import vm.types.slot as slot
from common.deco import pymethod, pyproperty


@po.pyimpl(constructor=False, iter_next=True)
@po.pyclass("generator")
@dataclass
class PyGenerator(po.PyClassImpl, slot.IterNextMixin, slot.IterNextIterableMixin):
    inner: Coro

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.generator_type

    def as_coro(self) -> Coro:
        return self.inner

    @staticmethod
    def new(frame: FrameRef, name: PyStrRef) -> PyGenerator:
        return PyGenerator(Coro.new(frame, name))

    @pyproperty()
    def get___name__(self, *, vm: VirtualMachine) -> PyStrRef:
        return self.inner.name

    @pyproperty()
    def set___name__(self, name: PyStrRef, *, vm: VirtualMachine) -> None:
        self.inner.set_name(name)

    @pymethod(True)
    @staticmethod
    def i__repr__(zelf: PyRef[PyGenerator], *, vm: VirtualMachine) -> str:
        return zelf._.inner.repr(zelf, zelf.get_id(), vm)

    @pymethod(True)
    @staticmethod
    def send(
        zelf: PyRef[PyGenerator], value: PyObjectRef, /, *, vm: VirtualMachine
    ) -> PyObjectRef:
        return zelf._.inner.send(zelf, value, vm).into_pyresult(vm)

    @pymethod(True)
    @staticmethod
    def throw(
        zelf: PyRef[PyGenerator],
        exc_type: PyObjectRef,
        exc_val: Optional[PyObjectRef] = None,
        exc_tb: Optional[PyObjectRef] = None,
        *,
        vm: VirtualMachine,
    ) -> PyObjectRef:
        return zelf._.inner.throw(
            zelf, exc_type, vm.unwrap_or_none(exc_val), vm.unwrap_or_none(exc_tb), vm
        ).into_pyresult(vm)

    @pymethod(True)
    @staticmethod
    def close(zelf: PyRef[PyGenerator], *, vm: VirtualMachine) -> None:
        zelf._.inner.close(zelf, vm)

    @pyproperty()
    def get_gi_frame(self, *, vm: VirtualMachine) -> FrameRef:
        return self.inner.frame

    @pyproperty()
    def get_gi_running(self, *, vm: VirtualMachine) -> bool:
        return self.inner.running

    @pyproperty()
    def get_gi_code(self, *, vm: VirtualMachine) -> PyRef[PyCode]:
        return self.inner.frame._.code

    @pyproperty()
    def get_gi_yieldfrom(self, *, vm: VirtualMachine) -> Optional[PyObjectRef]:
        return self.inner.frame._.yield_from_target(vm)

    @classmethod
    def next(cls, zelf: PyRef[PyGenerator], vm: VirtualMachine) -> PyIterReturn:
        return zelf._.inner.send(zelf, vm.ctx.get_none(), vm)


def init(ctx: PyContext) -> None:
    return PyGenerator.extend_class(ctx, ctx.types.generator_type)
