from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, TypeAlias
from common.hash import PyHash

if TYPE_CHECKING:
    from vm.builtins.pytype import PyTypeRef
    from vm.pyobject import PyContext
    from vm.pyobjectrc import PyObject, PyRef
    from vm.vm import VirtualMachine
import vm.pyobject as po
import vm.types.slot as slot


@po.tp_flags(basetype=True)
@po.pyimpl(constructor=True, comparable=True, hashable=True)
@po.pyclass("int")
@dataclass
class PyInt(
    po.PyClassImpl,
    po.PyValueMixin,
    po.TryFromObjectMixin,
    slot.HashableMixin,
    slot.ComparableMixin,
):
    value: int

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.int_type

    @staticmethod
    def special_retrieve(vm: VirtualMachine, obj: PyObject) -> Optional[PyRef[PyInt]]:
        return vm.to_index(obj)

    @staticmethod
    def from_(value: int) -> PyInt:
        return PyInt(value)

    @staticmethod
    def with_value(class_: PyTypeRef, value, vm: VirtualMachine) -> PyIntRef:
        if class_.is_(vm.ctx.types.int_type):
            return vm.ctx.new_int(value)
        elif class_.is_(vm.ctx.types.bool_type):
            return vm.ctx.new_bool(value != 0)
        else:
            return PyInt.from_(value).into_ref_with_type(vm, class_)

    def as_int(self) -> int:
        return self.value

    # TODO: impl Constructor for PyInt
    # TODO: impl PyInt @ 320

    @classmethod
    def cmp(
        cls,
        zelf: PyRef[PyInt],
        other: PyObject,
        op: slot.PyComparisonOp,
        vm: VirtualMachine,
    ) -> slot.PyComparisonValue:
        if (r := other.payload_if_subclass(PyInt, vm)) is not None:
            return slot.PyComparisonValue(op.eval_(zelf._.value, r.value))
        else:
            return slot.PyComparisonValue(None)

    @classmethod
    def hash(cls, zelf: PyRef[PyInt], vm: VirtualMachine) -> PyHash:
        return hash(zelf._.as_int())


PyIntRef: TypeAlias = "PyRef[PyInt]"


def get_value(obj: PyObject) -> int:
    r = obj.payload_(PyInt)
    assert r is not None
    return r.value


# TODO:
# def try_int(obj: PyObject, vm: VirtualMachine) -> int:


def try_bigint_to_f64(i: int, vm: VirtualMachine) -> float:
    try:
        return float(i)
    except OverflowError as _:
        vm.new_overflow_error("int too large to convert to float")

    # r = i2f(i)
    # if r is None:
    #     vm.new_overflow_error("int too large to convert to float")
    # return r


# def i2f(i: int) -> Optional[float]:
#     r = float(i)
#     if math.isfinite(r):
#         return r
#     else:
#         return None


def init(context: PyContext) -> None:
    PyInt.extend_class(context, context.types.int_type)
