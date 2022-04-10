from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from vm.pyobject import PyClassImpl, PyContext, PyValueMixin, pyclass, pyimpl, tp_flags
    from protocol.iter import PyIter
import vm.pyobject as po


@po.tp_flags(basetype=True)
@po.pyimpl(iter_next=True, constructor=True)
@po.pyclass("zip")
@dataclass
class PyZip(po.PyClassImpl, po.PyValueMixin):
    iterators: list[PyIter]
    strict: bool

    # TODO: impl Constructor for PyZip
    # TODO: impl PyZip @ 42
    # TODO: impl IterNextIterable for PyZip
    # TODO: impl IterNext for PyZip


def init(context: PyContext) -> None:
    PyZip.extend_class(context, context.types.zip_type)
