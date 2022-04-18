from __future__ import annotations
from dataclasses import dataclass


@dataclass
class PyBytesInner:
    elements: bytearray

    @staticmethod
    def from_(elements: bytearray) -> PyBytesInner:
        return PyBytesInner(elements)
