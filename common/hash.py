from __future__ import annotations
from dataclasses import dataclass
import random
from typing import TYPE_CHECKING, Any, Callable, Iterable, TypeVar

if TYPE_CHECKING:
    from vm.vm import VirtualMachine

PyHash = int


@dataclass
class HashSecret:
    k0: int
    k1: int

    @staticmethod
    def new(seed: int) -> HashSecret:
        buf = [0] * 16
        raise NotImplementedError

    @staticmethod
    def random() -> HashSecret:
        mk = lambda: random.randrange(0, (1 << 32) - 1)
        return HashSecret(mk(), mk())

    def hash_iter(self, elements: Iterable[T], hashf: Callable[[T], PyHash]) -> PyHash:
        raise NotImplementedError

    def hash_iter_unordered(
        self, elements: Iterable[T], hashf: Callable[[T], PyHash]
    ) -> PyHash:
        raise NotImplementedError


T = TypeVar("T")


def hash_iter(elements: Iterable, vm: VirtualMachine) -> PyHash:
    return vm.state.hash_secret.hash_iter(elements, lambda obj: obj.hash(vm))


def hash_iter_unordered(elements: Iterable, vm: VirtualMachine) -> PyHash:
    return vm.state.hash_secret.hash_iter_unordered(elements, lambda obj: obj.hash(vm))
