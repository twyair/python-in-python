from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING
from common.hash import PyHash

if TYPE_CHECKING:
    from vm.builtins.pytype import PyTypeRef
    from vm.builtins.tuple import PyTupleRef
    from vm.pyobject import PyContext
    from vm.pyobjectrc import PyRef, PyObject, PyObjectRef
    from vm.vm import VirtualMachine

import vm.pyobject as po
import vm.types.slot as slot
import vm.protocol.mapping as mapping
import vm.builtins.pystr as pystr


@po.tp_flags(basetype=True)
@po.pyimpl(hashable=True, comparable=True, as_mapping=True)
@po.pyclass("UnionType")
@dataclass
class PyUnion(
    po.PyClassImpl,
    slot.AsMappingMixin,
    slot.ComparableMixin,
    slot.HashableMixin,
    slot.GetAttrMixin,
):
    args: PyTupleRef
    parameters: PyTupleRef

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.union_type

    # TODO: impl PyUnion @ 34
    # TODO: impl PyUnion @ 201

    @classmethod
    def as_mapping(
        cls, zelf: PyRef[PyUnion], vm: VirtualMachine
    ) -> mapping.PyMappingMethods:
        raise NotImplementedError

    @classmethod
    def cmp(
        cls,
        zelf: PyRef[PyUnion],
        other: PyObject,
        op: slot.PyComparisonOp,
        vm: VirtualMachine,
    ) -> po.PyComparisonValue:
        raise NotImplementedError

    @classmethod
    def hash(cls, zelf: PyRef[PyUnion], vm: VirtualMachine) -> PyHash:
        raise NotImplementedError

    @classmethod
    def getattro(
        cls, zelf: PyRef[PyUnion], name: pystr.PyStrRef, vm: VirtualMachine
    ) -> PyObjectRef:
        raise NotImplementedError


def init(context: PyContext) -> None:
    PyUnion.extend_class(context, context.types.union_type)
