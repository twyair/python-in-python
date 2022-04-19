from __future__ import annotations
from dataclasses import dataclass
import math
from typing import TYPE_CHECKING, Callable, Optional, TypeAlias


if TYPE_CHECKING:
    from vm.builtins.pytype import PyTypeRef
    from vm.pyobject import PyContext
    from vm.pyobjectrc import PyObject, PyRef, PyObjectRef
    from vm.vm import VirtualMachine
    from vm.function_ import FuncArgs
    from vm.builtins.pystr import PyStrRef
import vm.pyobject as po
import vm.types.slot as slot
from common.deco import pymethod, pyproperty
from common.error import PyImplError
from common.hash import PyHash


@po.tp_flags(basetype=True)
@po.pyimpl(constructor=True, comparable=True, hashable=True)
@po.pyclass("int")
@dataclass
class PyInt(
    po.PyClassImpl,
    slot.HashableMixin,
    slot.ComparableMixin,
    slot.ConstructorMixin,
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

    def int_op(
        self, other: PyObjectRef, op: Callable[[int, int], int], vm: VirtualMachine
    ) -> po.PyArithmeticValue[int]:
        r = other.payload_if_subclass(PyInt, vm)
        if r is None:
            return po.PyArithmeticValue(None)
        else:
            return po.PyArithmeticValue(op(self.value, r.value))

    def general_op(
        self,
        other: PyObjectRef,
        op: Callable[[int, int], PyObjectRef],
        vm: VirtualMachine,
    ):
        if (v := other.payload_if_subclass(PyInt, vm)) is not None:
            return op(self.value, v.value)
        else:
            return vm.ctx.get_not_implemented()

    @pymethod(True)
    def i__add__(
        self, other: PyObjectRef, *, vm: VirtualMachine
    ) -> po.PyArithmeticValue[int]:
        return self.int_op(other, lambda a, b: a + b, vm)

    @pymethod(True)
    def i__radd__(
        self, other: PyObjectRef, *, vm: VirtualMachine
    ) -> po.PyArithmeticValue[int]:
        return self.i__add__(other, vm=vm)

    @pymethod(True)
    def i__sub__(
        self, other: PyObjectRef, *, vm: VirtualMachine
    ) -> po.PyArithmeticValue[int]:
        return self.int_op(other, lambda a, b: a - b, vm)

    @pymethod(True)
    def i__rsub__(
        self, other: PyObjectRef, *, vm: VirtualMachine
    ) -> po.PyArithmeticValue[int]:
        return self.int_op(other, lambda a, b: b - a, vm)

    @pymethod(True)
    def i__mul__(
        self, other: PyObjectRef, *, vm: VirtualMachine
    ) -> po.PyArithmeticValue[int]:
        return self.int_op(other, lambda a, b: a * b, vm)

    @pymethod(True)
    def i__rmul__(
        self, other: PyObjectRef, *, vm: VirtualMachine
    ) -> po.PyArithmeticValue[int]:
        return self.i__mul__(other, vm=vm)

    @pymethod(True)
    def i__truediv__(self, other: PyObjectRef, *, vm: VirtualMachine) -> PyObjectRef:
        return self.general_op(other, lambda a, b: inner_truediv(a, b, vm), vm)

    @pymethod(True)
    def i__rtruediv__(self, other: PyObjectRef, *, vm: VirtualMachine) -> PyObjectRef:
        return self.general_op(other, lambda a, b: inner_truediv(b, a, vm), vm)

    @pymethod(True)
    def i__floordiv__(self, other: PyObjectRef, *, vm: VirtualMachine) -> PyObjectRef:
        return self.general_op(other, lambda a, b: inner_floordiv(a, b, vm), vm)

    @pymethod(True)
    def i__rfloordiv__(self, other: PyObjectRef, *, vm: VirtualMachine) -> PyObjectRef:
        return self.general_op(other, lambda a, b: inner_floordiv(b, a, vm), vm)

    @pymethod(True)
    def i__lshift__(self, other: PyObjectRef, *, vm: VirtualMachine) -> PyObjectRef:
        return self.general_op(
            other, lambda a, b: inner_shift(a, b, lambda a, b: a << b, vm), vm
        )

    @pymethod(True)
    def i__rlshift__(self, other: PyObjectRef, *, vm: VirtualMachine) -> PyObjectRef:
        return self.general_op(
            other, lambda a, b: inner_shift(b, a, lambda a, b: a << b, vm), vm
        )

    @pymethod(True)
    def i__rshift__(self, other: PyObjectRef, *, vm: VirtualMachine) -> PyObjectRef:
        return self.general_op(
            other, lambda a, b: inner_shift(a, b, lambda a, b: a >> b, vm), vm
        )

    @pymethod(True)
    def i__rrshift__(self, other: PyObjectRef, *, vm: VirtualMachine) -> PyObjectRef:
        return self.general_op(
            other, lambda a, b: inner_shift(b, a, lambda a, b: a >> b, vm), vm
        )

    @pymethod(True)
    def i__xor__(
        self, other: PyObjectRef, *, vm: VirtualMachine
    ) -> po.PyArithmeticValue[int]:
        return self.int_op(other, lambda a, b: a ^ b, vm)

    @pymethod(True)
    def i__rxor__(
        self, other: PyObjectRef, *, vm: VirtualMachine
    ) -> po.PyArithmeticValue[int]:
        return self.i__xor__(other, vm=vm)

    @pymethod(True)
    def i__or__(
        self, other: PyObjectRef, *, vm: VirtualMachine
    ) -> po.PyArithmeticValue[int]:
        return self.int_op(other, lambda a, b: a | b, vm)

    @pymethod(True)
    def i__ror__(
        self, other: PyObjectRef, *, vm: VirtualMachine
    ) -> po.PyArithmeticValue[int]:
        return self.i__or__(other, vm=vm)

    @pymethod(True)
    def i__and__(
        self, other: PyObjectRef, *, vm: VirtualMachine
    ) -> po.PyArithmeticValue[int]:
        return self.int_op(other, lambda a, b: a & b, vm)

    @pymethod(True)
    def i__rand__(
        self, other: PyObjectRef, *, vm: VirtualMachine
    ) -> po.PyArithmeticValue[int]:
        return self.i__and__(other, vm=vm)

    @pymethod(True)
    def i__pow__(
        self, other: PyObjectRef, mod_val: Optional[PyObjectRef], *, vm: VirtualMachine
    ) -> PyObjectRef:
        raise NotImplementedError

    @pymethod(True)
    def i__rpow__(self, other: PyObjectRef, *, vm: VirtualMachine) -> PyObjectRef:
        return self.general_op(other, lambda a, b: inner_pow(b, a, vm), vm)

    @pymethod(True)
    def i__mod__(self, other: PyObjectRef, *, vm: VirtualMachine) -> PyObjectRef:
        return self.general_op(other, lambda a, b: inner_mod(a, b, vm), vm)

    @pymethod(True)
    def i__rmod__(self, other: PyObjectRef, *, vm: VirtualMachine) -> PyObjectRef:
        return self.general_op(other, lambda a, b: inner_mod(b, a, vm), vm)

    @pymethod(True)
    def i__divmod__(self, other: PyObjectRef, *, vm: VirtualMachine) -> PyObjectRef:
        return self.general_op(other, lambda a, b: inner_divmod(a, b, vm), vm)

    @pymethod(True)
    def i__rdivmod__(self, other: PyObjectRef, *, vm: VirtualMachine) -> PyObjectRef:
        return self.general_op(other, lambda a, b: inner_divmod(b, a, vm), vm)

    @pymethod(True)
    def i__neg__(self, *, vm: VirtualMachine) -> int:
        return -self.value

    @pymethod(True)
    def i__abs__(self, *, vm: VirtualMachine) -> int:
        return abs(self.value)

    @pymethod(True)
    @staticmethod
    def i__round__(
        zelf: PyRef[PyInt],
        precision: Optional[PyObjectRef] = None,
        *,
        vm: VirtualMachine,
    ) -> PyRef[PyInt]:
        if precision is not None and (
            vm.is_none(precision) or precision.payload_if_subclass(PyInt, vm)
        ):
            vm.new_type_error(
                f"'{precision.class_()._.name()}' object cannot be interpreted as an integer"
            )
        return zelf

    @pymethod(True)
    @staticmethod
    def i__int__(zelf: PyRef[PyInt], *, vm: VirtualMachine) -> PyRef[PyInt]:
        return zelf

    @pymethod(True)
    def i__pos__(self, *, vm: VirtualMachine) -> int:
        return self.value

    @pymethod(True)
    def i__float__(self, *, vm: VirtualMachine) -> float:
        return try_to_float(self.value, vm)

    @pymethod(True)
    @staticmethod
    def i__trunc__(zelf: PyRef[PyInt], *, vm: VirtualMachine) -> PyRef[PyInt]:
        return zelf

    @pymethod(True)
    @staticmethod
    def i__floor__(zelf: PyRef[PyInt], *, vm: VirtualMachine) -> PyRef[PyInt]:
        return zelf

    @pymethod(True)
    @staticmethod
    def i__ceil__(zelf: PyRef[PyInt], *, vm: VirtualMachine) -> PyRef[PyInt]:
        return zelf

    @pymethod(True)
    @staticmethod
    def i__index__(zelf: PyRef[PyInt], *, vm: VirtualMachine) -> PyRef[PyInt]:
        return zelf

    @pymethod(True)
    def i__invert__(self, *, vm: VirtualMachine) -> int:
        return ~self.value

    @pymethod(True)
    def i__repr__(self, *, vm: VirtualMachine) -> str:
        return str(self.value)

    @pymethod(True)
    def i__format__(self, spec: PyStrRef, *, vm: VirtualMachine) -> str:
        raise NotImplementedError

    @pymethod(True)
    def i__bool__(self, *, vm: VirtualMachine) -> bool:
        return self.value != 0

    @pymethod(True)
    def i__sizeof__(self, *, vm: VirtualMachine) -> int:
        return self.value.__sizeof__()

    @pymethod(True)
    def as_integer_ratio(self, *, vm: VirtualMachine) -> PyObjectRef:
        return vm.ctx.new_tuple([vm.ctx.new_int(self.value), vm.ctx.new_int(1)])

    @pymethod(True)
    def bit_length(self, *, vm: VirtualMachine) -> int:
        return self.value.bit_length()

    @pymethod(True)
    @staticmethod
    def conjugate(zelf: PyRef[PyInt], *, vm: VirtualMachine) -> PyRef[PyInt]:
        return zelf

    # TODO: impl from_bytes(), to_bytes()

    @pyproperty()
    def get_real(self, *, vm: VirtualMachine) -> PyRef[PyInt]:
        return vm.ctx.new_int(self.value)

    @pyproperty()
    def get_imag(self, *, vm: VirtualMachine) -> int:
        return 0

    @pyproperty()
    @staticmethod
    def get_numerator(zelf: PyRef[PyInt], *, vm: VirtualMachine) -> PyRef[PyInt]:
        return zelf

    @pyproperty()
    def get_denominator(self, *, vm: VirtualMachine) -> int:
        return 1

    @pymethod(True)
    def bit_count(self, *, vm: VirtualMachine) -> int:
        return self.value.bit_count()

    @pymethod(True)
    def i__getnewargs__(self, *, vm: VirtualMachine) -> PyObjectRef:
        return vm.ctx.new_tuple([vm.ctx.new_int(self.value)])

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

    @classmethod
    def py_new(
        cls, class_: PyTypeRef, fargs: FuncArgs, vm: VirtualMachine
    ) -> PyObjectRef:
        args = fargs.bind(__int_options)
        value: PyObjectRef = args.arguments["value"]
        base_arg: PyObjectRef = args.arguments["base"]
        if value is not None:
            if base_arg is not None:
                base = vm.to_index(base_arg)._.as_int()
                if not (base == 0 or 2 <= base <= 36):
                    vm.new_value_error("int() base must be >= 2 and <= 36, or 0")
                ret = try_int_radix(value, base, vm)
            else:
                if class_.is_(vm.ctx.types.int_type):
                    try:
                        i = value.downcast_exact(PyInt, vm)
                    except PyImplError as e:
                        v = e.obj
                    else:
                        return i
                else:
                    v = value
                ret = try_int(v, vm)
        elif base_arg is not None:
            vm.new_type_error("int() missing string argument")
        else:
            ret = 0

        return PyInt.with_value(class_, ret, vm)


PyIntRef: TypeAlias = "PyRef[PyInt]"


def __int_options(
    value: Optional[PyObjectRef] = None, /, base: Optional[PyObjectRef] = None
):
    ...


def inner_pow(int1: int, int2: int, vm: VirtualMachine) -> PyObjectRef:
    import vm.builtins.float as pyfloat  # FIXME

    if int2 < 0:
        v1 = try_to_float(int1, vm)
        v2 = try_to_float(int2, vm)
        return pyfloat.float_pow(v1, v2, vm)
    else:
        r = int1**int2
        assert isinstance(r, int)
        return vm.ctx.new_int(r)


def inner_mod(int1: int, int2: int, vm: VirtualMachine) -> PyObjectRef:
    if int2 == 0:
        vm.new_zero_division_error("integer module by zero")
    else:
        return vm.ctx.new_int(int1 % int2)


def inner_floordiv(int1: int, int2: int, vm: VirtualMachine) -> PyObjectRef:
    if int2 == 0:
        vm.new_zero_division_error("integer division by zero")
    else:
        return vm.ctx.new_int(int1 // int2)


def inner_divmod(int1: int, int2: int, vm: VirtualMachine) -> PyObjectRef:
    if int2 == 0:
        vm.new_zero_division_error("integer division or modulo by zero")
    return vm.new_tuple([vm.ctx.new_int(x) for x in divmod(int1, int2)])


def inner_shift(
    int1: int, int2: int, shift_op: Callable[[int, int], int], vm: VirtualMachine
) -> PyObjectRef:
    if int2 < 0:
        vm.new_value_error("negative shift count")
    elif int1 == 0:
        return vm.ctx.new_int(0)
    else:
        # TODO? check for overflow?
        return vm.ctx.new_int(shift_op(int1, int2))


def inner_truediv(i1: int, i2: int, vm: VirtualMachine) -> PyObjectRef:
    if i2 == 0:
        vm.new_zero_division_error("integer division by zero")

    try:
        ret = i1 / i2
    except OverflowError as _:
        vm.new_overflow_error("int too large to convert to float")
    return vm.ctx.new_float(ret)


def get_value(obj: PyObject) -> int:
    r = obj.payload_(PyInt)
    assert r is not None
    return r.value


def try_int_radix(obj: PyObjectRef, base: int, vm: VirtualMachine) -> int:
    raise NotImplementedError


def try_int(obj: PyObject, vm: VirtualMachine) -> int:
    raise NotImplementedError


def try_bigint_to_f64(i: int, vm: VirtualMachine) -> float:
    try:
        return float(i)
    except OverflowError as _:
        vm.new_overflow_error("int too large to convert to float")


def try_to_float(i: int, vm: VirtualMachine) -> float:
    r = i2f(i)
    if r is None:
        vm.new_overflow_error("int too large to convert to float")
    return r


def i2f(i: int) -> Optional[float]:
    r = float(i)
    if math.isfinite(r):
        return r
    else:
        return None


def init(context: PyContext) -> None:
    PyInt.extend_class(context, context.types.int_type)
