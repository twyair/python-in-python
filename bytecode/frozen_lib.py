from typing import Any, Iterable, Iterator
from bytecode.bytecode import FrozenModule


def decode_lib(bs: bytes) -> Iterable[tuple[str, FrozenModule]]:
    return bs


def encode_lib(lib: Iterable[tuple[str, FrozenModule]]) -> bytes:
    return lib
