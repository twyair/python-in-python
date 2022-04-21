from __future__ import annotations
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from vm.builtins.pytype import PyTypeRef
    from vm.pyobjectrc import PyObjectRef
    from vm.vm import VirtualMachine
    from vm.pyobject import PyContext


def extend_module(
    vm: VirtualMachine, module: PyObjectRef, attrs: dict[str, PyObjectRef]
) -> None:
    for name, value in attrs.items():
        vm.module_set_attr(module, vm.ctx.new_str(name), value)


def extend_class(
    context: PyContext, typ: PyTypeRef, attrs: dict[str, PyObjectRef]
) -> None:
    for name, value in attrs.items():
        typ._.set_str_attr(name, value)
