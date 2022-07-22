from __future__ import annotations
from typing import TYPE_CHECKING, Callable, Dict, TypeAlias
import vm.stdlib.imp
import vm.stdlib.io
import vm.stdlib.thread
import vm.stdlib.weakref
import vm.stdlib.warnings

if TYPE_CHECKING:
    from vm.vm import VirtualMachine
    from vm.pyobjectrc import PyObjectRef

# TODO: py_dyn_fn!
StdlibInitFunc: TypeAlias = Callable[["VirtualMachine"], "PyObjectRef"]

StdlibMap = Dict[str, StdlibInitFunc]


# FIXME!!!!
def get_module_inits() -> StdlibMap:
    return {
        "_imp": vm.stdlib.imp.make_module,
        "_io": vm.stdlib.io.make_module,
        "_thread": vm.stdlib.thread.make_module,
        "_warnings": vm.stdlib.warnings.make_module,
        "_weakref": vm.stdlib.weakref.make_module,
    }
