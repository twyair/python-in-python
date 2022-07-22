from __future__ import annotations

from typing import TYPE_CHECKING
from common.deco import pyfunction, pymodule
from vm.function_ import FuncArgs
from vm.pyobjectrc import InstanceDict


if TYPE_CHECKING:
    from vm.vm import VirtualMachine
    from vm.pyobjectrc import PyObjectRef
import vm.pyobject as po


@pymodule
class _thread(po.PyModuleImpl):
    # TODO!!!!!
    @pyfunction(True)
    @staticmethod
    def allocate_lock(*, vm: VirtualMachine) -> PyObjectRef:
        # FIXME
        return None

    @pyfunction(True)
    @staticmethod
    def get_ident(*, vm: VirtualMachine) -> int:
        # FIXME
        return 0


def make_module(vm: VirtualMachine) -> PyObjectRef:
    return _thread.make_module(vm)
