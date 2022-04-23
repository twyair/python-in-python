from __future__ import annotations

from typing import TYPE_CHECKING
from common.deco import pyfunction, pymodule


if TYPE_CHECKING:
    from vm.vm import VirtualMachine
    from vm.pyobjectrc import PyObjectRef
    from vm.builtins.pystr import PyStrRef
import vm.pyobject as po


@pymodule
class _imp(po.PyModuleImpl):
    # TODO!!!!!
    @pyfunction(True)
    @staticmethod
    def is_frozen(name: PyStrRef, *, vm: VirtualMachine) -> bool:
        return name._.as_str() in vm.state.frozen


def make_module(vm: VirtualMachine) -> PyObjectRef:
    return _imp.make_module(vm)
