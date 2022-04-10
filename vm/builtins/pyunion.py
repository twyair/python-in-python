from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from vm.builtins.pytype import PyTypeRef
    from vm.builtins.tuple import PyTupleRef
    from vm.pyobject import PyClassImpl, PyContext, PyValueMixin, pyclass, pyimpl, tp_flags
    from vm.vm import VirtualMachine

import vm.pyobject as po

@po.tp_flags(basetype=True)
@po.pyimpl(hashable=True, comparable=True, as_mapping=True)
@po.pyclass("UnionType")
@dataclass
class PyUnion(po.PyClassImpl, po.PyValueMixin):
    args: PyTupleRef
    parameters: PyTupleRef

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.union_type

    # TODO: impl PyUnion @ 34
    # TODO: impl PyUnion @ 201
    # TODO: impl AsMapping for PyUnion
    # TODO: impl Comparable for PyUnion
    # TODO: impl Hashable for PyUnion
    # TODO: impl GetAttr for PyUnion


def init(context: PyContext) -> None:
    PyUnion.extend_class(context, context.types.union_type)
