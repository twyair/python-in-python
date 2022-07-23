from __future__ import annotations
from abc import ABC
from dataclasses import dataclass
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from vm.builtins.slice import SaturatedSlice
    from vm.pyobjectrc import PyObject
    from vm.vm import VirtualMachine

import vm.builtins.slice as pyslice
import vm.builtins.int as pyint


@dataclass
class SequenceIndex(ABC):
    @staticmethod
    def try_from_borrowed_object(
        vm: VirtualMachine, obj: PyObject
    ) -> SequenceIndexInt | SequenceIndexSlice:
        if (i := obj.payload_(pyint.PyInt)) is not None:
            return SequenceIndexInt(i.as_int())
        elif (slice := obj.payload_(pyslice.PySlice)) is not None:
            return SequenceIndexSlice(slice.to_saturated(vm))
        elif (t := vm.to_index_opt(obj)) is not None:
            return SequenceIndexInt(t._.as_int())
        else:
            vm.new_type_error(
                f"indices must be integers or slices or classes that override __index__ operator, not '{obj.class_()}'"
            )


@dataclass
class SequenceIndexInt(SequenceIndex):
    value: int


@dataclass
class SequenceIndexSlice(SequenceIndex):
    value: SaturatedSlice
