from __future__ import annotations
from typing import TYPE_CHECKING, Iterator


if TYPE_CHECKING:
    from vm.pyobjectrc import PyObjectRef
    from vm.vm import VirtualMachine

from common.hash import PyHash


def hash_iter(it: Iterator[PyObjectRef], vm: VirtualMachine) -> PyHash:
    raise NotImplementedError
