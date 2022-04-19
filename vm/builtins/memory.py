from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING
from common.hash import PyHash

if TYPE_CHECKING:
    from vm.builtins.pytype import PyTypeRef
    from vm.protocol.buffer import BufferDescriptor, PyBuffer
    from vm.pyobject import PyContext
    from vm.vm import VirtualMachine
import vm.pyobject as po


@po.pyimpl(
    hashable=True,
    comparable=True,
    as_buffer=True,
    as_mapping=True,
    as_sequence=True,
    constructor=True,
)
@po.pyclass("memoryview")
@dataclass
class PyMemoryView(po.PyClassImpl):
    buffer: PyBuffer
    released: bool
    start: int
    format_spec: FormatSpec  # import from stdlib.pystruct
    desc: BufferDescriptor
    hash: PyHash

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.memoryview_type


def init(ctx: PyContext) -> None:
    PyMemoryView.extend_class(ctx, ctx.types.memoryview_type)
