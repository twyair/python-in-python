from __future__ import annotations
from dataclasses import dataclass

from typing import TYPE_CHECKING
from common.deco import pyfunction, pymethod, pymodule
from vm.builtins.pytype import PyTypeRef
from vm.function_ import FuncArgs
from vm.pyobjectrc import InstanceDict
from vm.types import slot


if TYPE_CHECKING:
    from vm.vm import VirtualMachine
    from vm.pyobjectrc import PyObjectRef
import vm.pyobject as po


# FIXME
@po.pyimpl()
@po.pyclass("__lock")
@dataclass
class Lock(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        # FIXME
        cell = Lock.static_cell()
        if cell is None:
            return cls.init_bare_type()
        return cell

    @pymethod(True)
    def i__enter__(self, *, vm: VirtualMachine) -> None:
        return

    @pymethod(True)
    def i__exit__(
        self,
        exc_type: PyObjectRef,
        exc_value: PyObjectRef,
        traceback: PyObjectRef,
        *,
        vm: VirtualMachine,
    ) -> None:
        return

    @pymethod(True)
    def acquire(self, *, vm: VirtualMachine) -> None:
        return

    @pymethod(True)
    def release(self, *, vm: VirtualMachine) -> None:
        return


@pymodule
class _thread(po.PyModuleImpl):
    # TODO!!!!!
    @pyfunction(True)
    @staticmethod
    def allocate_lock(*, vm: VirtualMachine) -> PyObjectRef:
        # FIXME
        return Lock().into_ref(vm)

    @pyfunction(True)
    @staticmethod
    def get_ident(*, vm: VirtualMachine) -> int:
        # FIXME
        return 0


def make_module(vm: VirtualMachine) -> PyObjectRef:
    Lock.extend_class(vm.ctx, Lock.class_(vm))
    return _thread.make_module(vm)
