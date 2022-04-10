from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, TypeAlias

if TYPE_CHECKING:
    from vm.builtins.pytype import PyTypeRef
    from vm.pyobject import (
        PyContext
    )
    from vm.pyobjectrc import PyObject, PyRef
    from vm.vm import VirtualMachine
import vm.pyobject as po

@po.tp_flags(basetype=True)
@po.pyimpl(constructor=True, comparable=True, hashable=True)
@po.pyclass("int")
@dataclass
class PyInt(po.PyClassImpl, po.PyValueMixin, po.TryFromObjectMixin):
    value: int

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.int_type

    # def into_object(self, vm: VirtualMachine) -> PyObjectRef:
    #     return vm.ctx.new_int(self.value)

    @staticmethod
    def special_retrieve(vm: VirtualMachine, obj: PyObject) -> Optional[PyRef[PyInt]]:
        return vm.to_index(obj)

    @staticmethod
    def from_(value: int) -> PyInt:
        return PyInt(value)

    # def into_ref(self, vm: VirtualMachine) -> PyIntRef:
    #     return PyRef[PyInt](vm.ctx.types.int_type, None, self)

    # def into_pyobj(self, vm: VirtualMachine) -> PyObjectRef:
    #     return self.into_ref(vm)

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
    # TODO: impl Comparable for PyInt
    # TODO: impl Hashable for PyInt


PyIntRef: TypeAlias = "PyRef[PyInt]"


def get_value(obj: PyObject) -> int:
    return obj.payload_(PyInt).value


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
