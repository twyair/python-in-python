from __future__ import annotations
from typing import TYPE_CHECKING
from common.deco import pymodule

# from vm.pyobject import PyModuleImpl

# from vm.pyobjectrc import PyObjectRef
import vm.pyobject as po

if TYPE_CHECKING:
    from vm.vm import VirtualMachine
    from vm.pyobjectrc import PyObjectRef


from vm import extend_module


def make_module(vm: VirtualMachine) -> PyObjectRef:
    module = _io.make_module(vm)

    # TODO
    # fileio.extend_module(vm, module)

    # unsupported_operation = _io.UNSUPPORTED_OPERATION
    extend_module(
        vm,
        module,
        {
            # TODO:
            # "UnsupportedOperation": unsupported_operation,
            "BlockingIOError": vm.ctx.exceptions.blocking_io_error,
        },
    )

    return module


@pymodule
class _io(po.PyModuleImpl):
    pass
