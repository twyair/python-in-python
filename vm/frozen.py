from __future__ import annotations
from typing import TYPE_CHECKING, Iterable
import vm.builtins.code as code
import bytecode.bytecode as bytecode

if TYPE_CHECKING:
    from vm.vm import VirtualMachine


def map_frozen(
    vm: VirtualMachine, i: Iterable[tuple[str, bytecode.FrozenModule]]
) -> Iterable[tuple[str, code.FrozenModule]]:
    return [
        (k, code.FrozenModule(vm.map_codeobj(mod.code), mod.package)) for k, mod in i
    ]


# FIXME!
def get_module_inits() -> Iterable[tuple[str, code.FrozenModule]]:
    return []
