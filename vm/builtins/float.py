from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional
if TYPE_CHECKING:
    from vm.builtins.int import PyInt, try_bigint_to_f64
    from vm.builtins.pytype import PyTypeRef
    from vm.pyobject import PyContext
    from vm.pyobjectrc import PyObject
    from vm.vm import VirtualMachine
import vm.pyobject as po

@po.tp_flags(basetype=True)
@po.pyimpl(comparable=True, hashable=True, constructor=True)
@po.pyclass("float")
@dataclass
class PyFloat(po.PyValueMixin, po.PyClassImpl, po.TryFromObjectMixin):
    value: float

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.float_type

    def to_float(self) -> float:
        return self.value

    @staticmethod
    def from_(value: float) -> PyFloat:
        return PyFloat(value)

    # TODO: impl Constructor for PyFloat
    # TODO: impl Comparable for PyFloat
    # TODO: impl Hashable for PyFloat
    # TODO: impl PyFloat @ 215


# TODO: impl PyObject @ 53 `try_to_f64`


def to_op_float(obj: PyObject, vm: VirtualMachine) -> Optional[float]:
    if (f := obj.payload_if_subclass(PyFloat, vm)) is not None:
        return f.value
    elif (i := obj.payload_if_subclass(PyInt, vm)) is not None:
        return try_bigint_to_f64(i.as_int(), vm)
    else:
        return None

def init(context: PyContext) -> None:
    PyFloat.extend_class(context, context.types.float_type)
