from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vm.pyobject import PyContext
    from vm.pyobjectrc import PyObjectWeak
import vm.pyobject as po


@po.pyimpl(set_attr=True, constructor=True)
@po.pyclass("weakproxy")
@dataclass
class PyWeakProxy(po.PyClassImpl):
    weak: PyObjectWeak


def init(ctx: PyContext) -> None:
    PyWeakProxy.extend_class(ctx, ctx.types.weakproxy_type)
