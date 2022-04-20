from __future__ import annotations
import sys

ISIZE_MAX: int = sys.maxsize
ISIZE_MIN: int = -sys.maxsize
CHAR_MAX: int = sys.maxunicode


def is_isize(n: int, /) -> bool:
    return ISIZE_MIN <= n <= ISIZE_MAX
