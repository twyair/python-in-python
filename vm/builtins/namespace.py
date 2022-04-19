from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vm.builtins.pytype import PyTypeRef
    from vm.pyobject import PyContext
    from vm.pyobjectrc import PyObjectRef, PyRef
    from vm.vm import VirtualMachine
import vm.pyobject as po
import vm.pyobjectrc as prc


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl(constructor=True, comparable=True)
@po.pyclass("SimpleNamespace")
@dataclass
class PyNamespace(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.namespace_type

    @staticmethod
    def new_ref(ctx: PyContext) -> PyRef[PyNamespace]:
        return prc.PyRef.new_ref(
            PyNamespace(), ctx.types.namespace_type, ctx.new_dict()
        )

    # TODO: impl Constructor for PyNamespace
    # TODO: impl Comparable for PyNamespace
    # TODO: impl PyNamespace @ 43


def init(context: PyContext) -> None:
    return PyNamespace.extend_class(context, context.types.namespace_type)
