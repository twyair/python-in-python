from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Optional, TypeAlias, Callable

from common import ISIZE_MAX

if TYPE_CHECKING:
    from vm.pyobjectrc import PyObjectRef, PyObject
    from vm.vm import VirtualMachine

Guard: TypeAlias = Any


class MutObjectSequenceOpMixin(ABC):
    @classmethod
    @abstractmethod
    def do_get(cls, index: int, guard) -> Optional[PyObjectRef]:
        ...

    @abstractmethod
    def do_lock(self):
        ...

    def mut_count(self, vm: VirtualMachine, needle: PyObject) -> int:
        count: int = 0

        def do() -> None:
            nonlocal count
            count += 1

        self._mut_iter_equal_skeleton(False, vm, needle, range(0, ISIZE_MAX), do)
        return count

    def mut_index_range(
        self, vm: VirtualMachine, needle: PyObject, range_: range
    ) -> Optional[int]:
        return self._mut_iter_equal_skeleton(True, vm, needle, range_, lambda: None)

    def mut_index(self, vm: VirtualMachine, needle: PyObject) -> Optional[int]:
        return self.mut_index_range(vm, needle, range(0, ISIZE_MAX))

    def mut_contains(self, vm: VirtualMachine, needle: PyObject) -> bool:
        return self.mut_index(vm, needle) is not None

    def _mut_iter_equal_skeleton(
        self,
        short: bool,
        vm: VirtualMachine,
        needle: PyObject,
        range: range,
        f: Callable[[], None],
    ) -> Optional[int]:
        raise NotImplementedError
