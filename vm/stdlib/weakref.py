from __future__ import annotations

from typing import TYPE_CHECKING
from common.deco import pyfunction, pymodule


if TYPE_CHECKING:
    from vm.vm import VirtualMachine
    from vm.pyobjectrc import PyObjectRef
    from vm.function_ import FuncArgs
import vm.pyobject as po


@pymodule
class _weakref(po.PyModuleImpl):
    # TODO!!!!!
    @pyfunction(False)
    @staticmethod
    def ref(args: FuncArgs, *, vm: VirtualMachine) -> PyObjectRef:
        # FIXME
        x, *_ = args.take_positional_range(0, 2)
        return x


def make_module(vm: VirtualMachine) -> PyObjectRef:
    return _weakref.make_module(vm)
