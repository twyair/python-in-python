from __future__ import annotations
import enum

class Mode(enum.Enum):
    Exec = "exec"
    Eval = "eval"
    Single = "single"
