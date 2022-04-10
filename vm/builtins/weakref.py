from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vm.pyobject import PyContext

import vm.pyobject as po


def init(ctx: PyContext) -> None:
    po.PyWeak.extend_class(ctx, ctx.types.weakref_type)
