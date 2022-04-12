from __future__ import annotations

ISIZE_MAX = 1 << 32
ISIZE_MIN = -ISIZE_MAX


def is_isize(n: int, /) -> bool:
    return ISIZE_MIN <= n <= ISIZE_MAX
