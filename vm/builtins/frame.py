from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vm.pyobject import PyContext
import vm.frame as frame


def init(context: PyContext) -> None:
    frame.Frame.extend_class(context, context.types.frame_type)
