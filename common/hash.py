from __future__ import annotations
from dataclasses import dataclass
import random

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
