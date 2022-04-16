from __future__ import annotations

from dataclasses import dataclass
import math
from typing import TYPE_CHECKING, Callable, Optional
from common.deco import pymethod, pyproperty
from vm.builtins.tuple import PyTupleRef

if TYPE_CHECKING:
    from vm.function_ import FuncArgs
    from vm.builtins.pytype import PyTypeRef
    from vm.pyobject import PyContext
    from vm.pyobjectrc import PyObject, PyObjectRef, PyRef
    from vm.vm import VirtualMachine
    from vm.builtins.pystr import PyStrRef

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

    @pymethod(True)
    def i__format__(self, spec: PyStrRef, *, vm: VirtualMachine) -> PyStrRef:
        raise NotImplementedError

    @pymethod(True)
    def i__abs__(self, *, vm: VirtualMachine) -> PyRef[PyFloat]:
        return vm.ctx.new_float(abs(self.value))

    def simple_op(
        self,
        other: PyObjectRef,
        op: Callable[[float, float], float],
        vm: VirtualMachine,
    ) -> PyObjectRef:
        r = to_op_float(other, vm)
        if r is None:
            return vm.ctx.get_not_implemented()
        else:
            return vm.ctx.new_float(op(self.value, r))

    def complex_op(
        self,
        other: PyObjectRef,
        op: Callable[[float, float], PyObjectRef],
        vm: VirtualMachine,
    ) -> PyObjectRef:
        r = to_op_float(other, vm)
        if r is None:
            return vm.ctx.get_not_implemented()
        else:
            return op(self.value, r)

    def tuple_op(
        self,
        other: PyObjectRef,
        op: Callable[[float, float], tuple[float, float]],
        vm: VirtualMachine,
    ) -> PyTupleRef:
        r = to_op_float(other, vm)
        if r is None:
            return vm.ctx.get_not_implemented()
        else:
            return vm.ctx.new_tuple([vm.ctx.new_float(v) for v in op(self.value, r)])

    @pymethod(True)
    def i__add__(self, other: PyObjectRef, *, vm: VirtualMachine) -> PyObjectRef:
        return self.simple_op(other, lambda a, b: a + b, vm)

    @pymethod(True)
    def i__radd__(self, other: PyObjectRef, *, vm: VirtualMachine) -> PyObjectRef:
        return self.i__add__(other, vm=vm)

    @pymethod(True)
    def i__bool__(self, *, vm: VirtualMachine) -> bool:
        return self.value != 0.0

    @pymethod(True)
    def i__divmod__(self, other: PyObjectRef, *, vm: VirtualMachine) -> PyTupleRef:
        return self.tuple_op(other, lambda a, b: inner_divmod(a, b, vm), vm)

    @pymethod(True)
    def i__rdivmod__(self, other: PyObjectRef, *, vm: VirtualMachine) -> PyTupleRef:
        return self.tuple_op(other, lambda a, b: inner_divmod(b, a, vm), vm)

    @pymethod(True)
    def i__floordiv__(self, other: PyObjectRef, *, vm: VirtualMachine) -> PyObjectRef:
        return self.simple_op(other, lambda a, b: inner_floordiv(a, b, vm), vm)

    @pymethod(True)
    def i__rfloordiv__(self, other: PyObjectRef, *, vm: VirtualMachine) -> PyObjectRef:
        return self.simple_op(other, lambda a, b: inner_floordiv(b, a, vm), vm)

    @pymethod(True)
    def i__mod__(self, other: PyObjectRef, *, vm: VirtualMachine) -> PyObjectRef:
        return self.simple_op(other, lambda a, b: inner_mod(a, b, vm), vm)

    @pymethod(True)
    def i__rmod__(self, other: PyObjectRef, *, vm: VirtualMachine) -> PyObjectRef:
        return self.simple_op(other, lambda a, b: inner_mod(b, a, vm), vm)

    @pymethod(True)
    def i__pos__(self, *, vm: VirtualMachine) -> float:
        return self.value

    @pymethod(True)
    def i__neg__(self, *, vm: VirtualMachine) -> float:
        return -self.value

    @pymethod(True)
    def i__pow__(
        self, other: PyObjectRef, mod_val: Optional[PyObjectRef], *, vm: VirtualMachine
    ) -> PyObjectRef:
        if mod_val is not None:
            vm.new_type_error("floating point pow() does not accept a 3rd argument")
        else:
            return self.complex_op(other, lambda a, b: float_pow(a, b, vm), vm)

    @pymethod(True)
    def i__rpow__(self, other: PyObjectRef, *, vm: VirtualMachine) -> PyObjectRef:
        return self.complex_op(other, lambda a, b: float_pow(b, a, vm), vm)

    @pymethod(True)
    def i__sub__(self, other: PyObjectRef, *, vm: VirtualMachine) -> PyObjectRef:
        return self.simple_op(other, lambda a, b: a - b, vm)

    @pymethod(True)
    def i__rsub__(self, other: PyObjectRef, *, vm: VirtualMachine) -> PyObjectRef:
        return self.simple_op(other, lambda a, b: b - a, vm)

    @pymethod(True)
    def i__repr__(self, *, vm: VirtualMachine) -> str:
        return repr(self.value)

    @pymethod(True)
    def i__truediv__(self, other: PyObjectRef, *, vm: VirtualMachine) -> PyObjectRef:
        return self.simple_op(other, lambda a, b: inner_div(a, b, vm), vm)

    @pymethod(True)
    def i__rtruediv__(self, other: PyObjectRef, *, vm: VirtualMachine) -> PyObjectRef:
        return self.simple_op(other, lambda a, b: inner_div(b, a, vm), vm)

    @pymethod(True)
    def i__mul__(self, other: PyObjectRef, *, vm: VirtualMachine) -> PyObjectRef:
        return self.simple_op(other, lambda a, b: a * b, vm)

    @pymethod(True)
    def i__rmul__(self, other: PyObjectRef, *, vm: VirtualMachine) -> PyObjectRef:
        return self.i__mul__(other, vm=vm)

    @pymethod(True)
    def i__trunc__(self, *, vm: VirtualMachine) -> int:
        return try_to_bigint(self.value, vm)

    @pymethod(True)
    def i__floor__(self, *, vm: VirtualMachine) -> int:
        return try_to_bigint(self.value.__floor__(), vm)

    @pymethod(True)
    def i__ceil__(self, *, vm: VirtualMachine) -> int:
        return try_to_bigint(self.value.__ceil__(), vm)

    # TODO:
    # @pymethod(True)
    # def round(...)

    @pymethod(True)
    def i__int__(self, *, vm: VirtualMachine) -> int:
        return self.i__trunc__(vm=vm)

    @pymethod(True)
    @classmethod
    def i__float__(cls, zelf: PyRef[PyFloat], *, vm: VirtualMachine) -> PyRef[PyFloat]:
        return zelf

    @pyproperty()
    @classmethod
    def get_real(cls, zelf: PyRef[PyFloat], *, vm: VirtualMachine) -> PyRef[PyFloat]:
        return zelf

    @pymethod(True)
    def get_imag(self, *, vm: VirtualMachine) -> float:
        return 0

    @pymethod(True)
    @classmethod
    def conjugate(cls, zelf: PyRef[PyFloat], *, vm: VirtualMachine) -> PyRef[PyFloat]:
        return zelf

    @pymethod(True)
    def is_integer(self, *, vm: VirtualMachine) -> bool:
        return self.value.is_integer()

    @pymethod(True)
    def as_integer_ratio(self, *, vm: VirtualMachine) -> PyTupleRef:
        if not math.isfinite(self.value):
            if math.isinf(self.value):
                vm.new_overflow_error("cannot convert Infinity to integer ratio")
            elif math.isnan(self.value):
                vm.new_value_error("cannot convert NaN to integer ratio")
            else:
                unreachable("{self.value} must be finite")

        return vm.ctx.new_tuple(
            [vm.ctx.new_int(x) for x in self.value.as_integer_ratio()]
        )

    # TODO: impl fromhex(), hex(), getnewargs()


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


def inner_div(v1: float, v2: float, vm: VirtualMachine) -> float:
    try:
        return v1 / v2
    except ZeroDivisionError as _:
        vm.new_zero_division_error("float division by zero")


def inner_mod(v1: float, v2: float, vm: VirtualMachine) -> float:
    try:
        return v1 % v2
    except ZeroDivisionError as _:
        vm.new_zero_division_error("float mod by zero")


def try_to_bigint(value: float, vm: VirtualMachine) -> int:
    if math.isinf(value):
        vm.new_overflow_error(
            "OverflowError: cannot convert float infinity to integer",
        )
    elif math.isnan(value):
        vm.new_value_error("ValueError: cannot convert float NaN to integer")
    else:
        return int(value)


def inner_floordiv(v1: float, v2: float, vm: VirtualMachine) -> float:
    try:
        return v1 // v2
    except ZeroDivisionError as _:
        vm.new_zero_division_error("float floordiv by zero")


def inner_divmod(v1: float, v2: float, vm: VirtualMachine) -> tuple[float, float]:
    try:
        return v1.__divmod__(v2)
    except ZeroDivisionError as _:
        vm.new_zero_division_error("float divmod()")


def float_pow(v1: float, v2: float, vm: VirtualMachine) -> PyObjectRef:
    if v1 == 0.0 and v2 < 0:
        vm.new_zero_division_error("{v1} cannot be raised to a negative power")
    else:
        r = v1**v2
        if isinstance(r, float):
            return vm.ctx.new_float(r)
        elif isinstance(r, complex):
            return vm.ctx.new_complex(r)
        else:
            assert False, r


def init(context: PyContext) -> None:
    PyFloat.extend_class(context, context.types.float_type)
