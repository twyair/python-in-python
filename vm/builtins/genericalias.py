from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from vm.builtins.pytype import PyTypeRef
    from vm.builtins.tuple import PyTupleRef
    from vm.pyobject import PyClassImpl, PyContext, PyValueMixin, pyclass, pyimpl, tp_flags
    from vm.pyobjectrc import PyObjectRef
    from vm.vm import VirtualMachine
import vm.pyobject as po

ATTR_EXCEPTIONS = [
    "__origin__",
    "__args__",
    "__parameters__",
    "__mro_entries__",
    "__reduce_ex__",
    "__reduce__",
    "__copy__",
    "__deepcopy__",
]


@po.tp_flags(basetype=True)
@po.pyimpl(
    as_mapping=True,
    callable=True,
    comparable=True,
    constructor=True,
    get_attr=True,
    hashable=True,
)
@po.pyclass("GenericAlias", module_name="types")
@dataclass
class PyGenericAlias(po.PyClassImpl, po.PyValueMixin):
    origin: PyTypeRef
    args: PyTupleRef
    parameters: PyTupleRef

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.generic_alias_type

    @staticmethod
    def new(origin: PyTypeRef, args: PyObjectRef, vm: VirtualMachine) -> PyGenericAlias:
        raise NotImplementedError

    def into_pyresult(self, vm: VirtualMachine) -> PyObjectRef:
        raise NotImplementedError

    # TODO: impl Constructor for PyGenericAlias
    # TODO: impl AsMapping for PyGenericAlias
    # TODO: impl Callable for PyGenericAlias
    # TODO: impl Comparable for PyGenericAlias
    # TODO: impl Hashable for PyGenericAlias
    # TODO: impl GetAttr for PyGenericAlias


def init(context: PyContext) -> None:
    PyGenericAlias.extend_class(context, context.types.generic_alias_type)
