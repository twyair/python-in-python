from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from vm.function.arguments import ArgMapping

if TYPE_CHECKING:
    from vm.builtins.dict import PyDictRef
    from vm.vm import VirtualMachine


@dataclass
class Scope:
    locals: ArgMapping
    globals: PyDictRef

    @staticmethod
    def new(locals: Optional[ArgMapping], globals: PyDictRef) -> Scope:
        if locals is None:
            locals = ArgMapping.from_dict_exact(globals)
        return Scope(locals=locals, globals=globals)

    @staticmethod
    def with_builtins(
        locals: Optional[ArgMapping], globals: PyDictRef, vm: VirtualMachine
    ) -> Scope:
        return Scope.new(locals, globals)
