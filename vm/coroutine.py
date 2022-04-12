from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional
from common.error import PyImplException
from vm.protocol.iter import PyIterReturn

from vm.pyobjectrc import PyObjectRef

if TYPE_CHECKING:
    from vm.builtins.pystr import PyStrRef
    from vm.exceptions import PyBaseExceptionRef
    from vm.frame import FrameRef
    from vm.vm import VirtualMachine
    from vm.pyobjectrc import PyObject


def gen_name(gen: PyObject, vm: VirtualMachine) -> str:
    typ = gen.class_()
    if typ.is_(vm.ctx.types.coroutine_type):
        return "coroutine"
    elif typ.is_(vm.ctx.types.async_generator):
        return "async generator"
    else:
        return "generator"


@dataclass
class Coro:
    frame: FrameRef
    closed: bool
    running: bool
    name: PyStrRef
    exception: Optional[PyBaseExceptionRef]

    @staticmethod
    def new(frame: FrameRef, name: PyStrRef) -> Coro:
        return Coro(frame=frame, closed=False, running=False, name=name, exception=None)

    def set_name(self, name: PyStrRef) -> None:
        self.name = name

    def send(
        self, gen: PyObject, vale: PyObjectRef, vm: VirtualMachine
    ) -> PyIterReturn:
        raise NotImplementedError

    def throw(
        self,
        gen: PyObject,
        exc_type: PyObjectRef,
        exc_val: PyObjectRef,
        exc_tb: PyObjectRef,
        vm: VirtualMachine,
    ) -> PyIterReturn:
        if self.closed:
            raise PyImplException(vm.normalize_exception(exc_type, exc_val, exc_tb))
        raise NotImplementedError

    def repr(self, gen: PyObject, id: int, vm: VirtualMachine) -> str:
        return "<{} object {} at {:x}>".format(gen_name(gen, vm), self.name, id)
