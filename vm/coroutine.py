from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from vm.builtins.pystr import PyStrRef
from vm.exceptions import PyBaseExceptionRef

from vm.frame import FrameRef


@dataclass
class Coro:
    frame: FrameRef
    closed: Optional[bool]
    running: Optional[bool]
    name: PyStrRef
    exception: Optional[PyBaseExceptionRef]
