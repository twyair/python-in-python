from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from vm.builtins.pytype import PyTypeRef
    from vm.frame import FrameRef
    from vm.pyobject import PyContext
    from vm.pyobjectrc import PyRef, PyObjectRef
    from vm.vm import VirtualMachine

import vm.pyobject as po
import vm.types.slot as slot
import vm.protocol.iter as viter
import vm.coroutine as coro
import vm.builtins.pystr as pystr
import vm.builtins.code as pycode

from common.deco import pymethod, pyproperty


@po.pyimpl(constructor=False, iter_next=True)
@po.pyclass("coroutine")
@dataclass
class PyCoroutine(
    po.PyClassImpl,
    slot.IterNextMixin,
    slot.IterNextIterableMixin,
):
    inner: coro.Coro

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.coroutine_type

    @staticmethod
    def new(frame: FrameRef, name: pystr.PyStrRef) -> PyCoroutine:
        return PyCoroutine(coro.Coro.new(frame, name))

    @pyproperty()
    def get___name__(self, *, vm: VirtualMachine) -> pystr.PyStrRef:
        return self.inner.name

    @pyproperty()
    def set___name__(self, name: pystr.PyStrRef, /, *, vm: VirtualMachine) -> None:
        self.inner.set_name(name)

    @pymethod(True)
    @staticmethod
    def i__repr__(zelf: PyRef[PyCoroutine], *, vm: VirtualMachine) -> str:
        return zelf._.inner.repr(zelf, zelf.get_id(), vm)

    @pymethod(True)
    @staticmethod
    def send(
        zelf: PyRef[PyCoroutine], value: PyObjectRef, /, *, vm: VirtualMachine
    ) -> PyObjectRef:
        return zelf._.inner.send(zelf, value, vm).into_pyresult(vm)

    @pymethod(True)
    @staticmethod
    def throw(
        zelf: PyRef[PyCoroutine],
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
    def close(zelf: PyRef[PyCoroutine], *, vm: VirtualMachine) -> None:
        zelf._.inner.close(zelf, vm)  # TODO

    @pymethod(True)
    @staticmethod
    def i__await__(zelf: PyRef[PyCoroutine]) -> PyCoroutineWrapper:
        return PyCoroutineWrapper(zelf)

    @pyproperty()
    def get_cr_await(self, *, vm: VirtualMachine) -> Optional[PyObjectRef]:
        return self.inner.frame._.yield_from_target(vm)  # TODO

    @pyproperty()
    def get_cr_frame(self, *, vm: VirtualMachine) -> FrameRef:
        return self.inner.frame

    @pyproperty()
    def get_cr_running(self, *, vm: VirtualMachine) -> bool:
        return self.inner.running

    @pyproperty()
    def get_cr_code(self, *, vm: VirtualMachine) -> PyRef[pycode.PyCode]:
        return self.inner.frame._.code

    @pyproperty()
    def get_cr_origin(self, *, vm: VirtualMachine) -> Optional[PyObjectRef]:
        raise NotImplementedError(
            "see https://docs.python.org/3/library/sys.html#sys.set_coroutine_origin_tracking_depth"
        )

    @classmethod
    def next(cls, zelf: PyRef[PyCoroutine], vm: VirtualMachine) -> viter.PyIterReturn:
        return zelf._.inner.send(zelf, vm.ctx.get_none(), vm)


@po.pyimpl(iter_next=True)
@po.pyclass("coroutine_wrapper")
@dataclass
class PyCoroutineWrapper(po.PyClassImpl):
    coro: PyRef[PyCoroutine]

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.coroutine_wrapper_type


def init(ctx: PyContext) -> None:
    PyCoroutine.extend_class(ctx, ctx.types.coroutine_type)
    PyCoroutineWrapper.extend_class(ctx, ctx.types.coroutine_wrapper_type)
