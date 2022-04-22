from __future__ import annotations

from typing import TYPE_CHECKING
from common.deco import pymodule


if TYPE_CHECKING:
    from vm.vm import VirtualMachine
    from vm.pyobjectrc import PyObjectRef
import vm.pyobject as po


@pymodule
class _imp(po.PyModuleImpl):
    # TODO!!!!!
    pass


def make_module(vm: VirtualMachine) -> PyObjectRef:
    return _imp.make_module(vm)
