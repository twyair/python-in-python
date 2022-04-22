from __future__ import annotations
from typing import TYPE_CHECKING, Callable, Dict, TypeAlias
import vm.stdlib.imp

if TYPE_CHECKING:
    from vm.vm import VirtualMachine
    from vm.pyobjectrc import PyObjectRef

# TODO: py_dyn_fn!
StdlibInitFunc: TypeAlias = Callable[["VirtualMachine"], "PyObjectRef"]

StdlibMap = Dict[str, StdlibInitFunc]


# FIXME!!!!
def get_module_inits() -> StdlibMap:
    return {"_imp": vm.stdlib.imp.make_module}
