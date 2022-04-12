from __future__ import annotations
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from vm.pyobjectrc import PyObjectRef, PyObject
    from vm.vm import VirtualMachine

import vm.pyobject as po
from common.deco import pyfunction, pymodule
from common.error import PyImplBase


@pymodule
class sys(po.PyModuleImpl):
    @pyfunction
    @staticmethod
    def get_stdout(vm: VirtualMachine) -> PyObjectRef:
        try:
            return vm.sys_module.get_attr(vm.mk_str("stdout"), vm)
        except PyImplBase as _:
            vm.new_runtime_error("lost sys.stdout")


def init_module(vm: VirtualMachine, module: PyObject, builtins: PyObject) -> None:
    # TODO:

    sys.extend_module(vm, module)  # TODO: add attributes `__doc__` and `modules`
