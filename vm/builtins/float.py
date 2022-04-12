from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from vm.function_ import FuncArgs
    from vm.builtins.pytype import PyTypeRef
    from vm.pyobject import PyContext
    from vm.pyobjectrc import PyObject, PyObjectRef, PyRef
    from vm.vm import VirtualMachine

import vm.builtins.bytearray as pybytearray
import vm.builtins.bytes as pybytes
import vm.builtins.int as pyint
import vm.builtins.pystr as pystr
import vm.function_ as fn
import vm.pyobject as po
import vm.types.slot as slot
from common.error import PyImplError, unreachable
from common.hash import PyHash


@po.tp_flags(basetype=True)
@po.pyimpl(comparable=True, hashable=True, constructor=True)
@po.pyclass("float")
@dataclass
class PyFloat(
    po.PyValueMixin,
    po.PyClassImpl,
    po.TryFromObjectMixin,
    slot.ConstructorMixin,
    slot.ComparableMixin,
    slot.HashableMixin,
):
    value: float

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.float_type

    def to_float(self) -> float:
        return self.value

    @staticmethod
    def from_(value: float) -> PyFloat:
        return PyFloat(value)

    @classmethod
    def py_new(
        cls, class_: PyTypeRef, args: FuncArgs, vm: VirtualMachine
    ) -> PyObjectRef:
        arg = args.take_positional_optional(lambda: vm.new_type_error("TODO"))
        if arg is None:
            float_val = 0.0
        else:
            if class_.is_(vm.ctx.types.float_type):
                try:
                    val = arg.downcast_exact(PyFloat, vm)
                except PyImplError as e:
                    val = e.obj
                else:
                    return val
            else:
                val = arg
            if (f := val.try_to_float(vm)) is not None:
                float_val = f
            else:
                float_val = float_from_string(val, vm)
        return cls.from_(float_val).into_ref(vm)

    @classmethod
    def cmp(
        cls,
        zelf: PyRef[PyFloat],
        other: PyObject,
        op: slot.PyComparisonOp,
        vm: VirtualMachine,
    ) -> slot.PyComparisonValue:
        if (val := other.payload_if_subclass(PyFloat, vm)) is not None:
            ret = op.eval_(zelf._.value, val.value)
        elif val := other.payload_if_subclass(pyint.PyInt, vm):
            ret = op.eval_(zelf._.value, val.as_int())
        else:
            return slot.PyComparisonValue(None)
        return po.PyComparisonValue(ret)

    @classmethod
    def hash(cls, zelf: PyRef[PyFloat], vm: VirtualMachine) -> PyHash:
        return hash(zelf._.value)

    # TODO: impl PyFloat @ 215


def float_from_string(val: PyObjectRef, vm: VirtualMachine) -> float:
    if (bs := val.payload_if_subclass(pystr.PyStr, vm)) is not None:
        b = bs.as_str()
    elif (bs := val.payload_if_subclass(pybytes.PyBytes, vm)) is not None:
        b = bs.inner
    elif (bs := val.payload_if_subclass(pybytearray.PyByteArray, vm)) is not None:
        b = bs.inner
    elif (bs := fn.ArgBytesLike.try_from_borrowed_object(vm, val)) is not None:
        b = bs.value.as_contiguous()
        assert b is not None
    else:
        vm.new_type_error(
            f"float() argument must be a string or a number, not '{val.class_()._.name()}'"
        )
    try:
        return float(b)
    except ValueError as _:
        vm.new_value_error(f"could not convert string to float: '{val.repr(vm)}'")
    unreachable()


def to_op_float(obj: PyObject, vm: VirtualMachine) -> Optional[float]:
    if (f := obj.payload_if_subclass(PyFloat, vm)) is not None:
        return f.value
    elif (i := obj.payload_if_subclass(pyint.PyInt, vm)) is not None:
        return pyint.try_bigint_to_f64(i.as_int(), vm)
    else:
        return None


def init(context: PyContext) -> None:
    PyFloat.extend_class(context, context.types.float_type)
