from __future__ import annotations
import sys
from typing import TYPE_CHECKING, Callable, Optional, TypeVar

from common.error import PyImplBase

if TYPE_CHECKING:
    from vm.pyobjectrc import PyObjectRef

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


def debug_repr(x: PyObjectRef) -> str:
    s = "..."
    if (f := getattr(x._, "debug_repr", None)) is not None:
        s = f()
    return f"<{type(x._)} '{s}'>"
