from __future__ import annotations
import sys
from typing import Callable, Optional, TypeVar

from common.error import PyImplBase

ISIZE_MAX: int = sys.maxsize
ISIZE_MIN: int = -sys.maxsize
CHAR_MAX: int = sys.maxunicode


def is_isize(n: int, /) -> bool:
    return ISIZE_MIN <= n <= ISIZE_MAX


T = TypeVar("T")


def to_opt(f: Callable[[], T]) -> Optional[T]:
    try:
        return f()
    except PyImplBase as _:
        return None
