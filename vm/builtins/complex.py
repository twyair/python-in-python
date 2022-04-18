from __future__ import annotations
from dataclasses import dataclass
import operator
from typing import TYPE_CHECKING, Callable, Optional
from common.deco import pymethod, pyproperty
from common.error import PyImplBase
from common.hash import PyHash

if TYPE_CHECKING:
    from vm.builtins.float import PyFloat
    from vm.builtins.pystr import PyStr
    from vm.builtins.pytype import PyTypeRef
    from vm.pyobject import PyComparisonValue, PyContext
    from vm.pyobjectrc import PyObject, PyObjectRef, PyRef
    from vm.types.slot import PyComparisonOp
    from vm.vm import VirtualMachine

import vm.pyobject as po
import vm.pyobjectrc as prc
import vm.types.slot as slot
import vm.builtins.float as pyfloat
import vm.builtins.pystr as pystr
import vm.function_ as fn


@po.tp_flags(basetype=True)
@po.pyimpl(comparable=True, hashable=True, constructor=True)
@po.pyclass("complex")
@dataclass
class PyComplex(
    po.PyValueMixin,
    po.PyClassImpl,
    po.TryFromObjectMixin,
    slot.ComparableMixin,
    slot.HashableMixin,
    slot.ConstructorMixin,
):
    value: complex

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.complex_type

    @staticmethod
    def new_ref(value: complex, ctx: PyContext) -> PyRef[PyComplex]:
        return prc.PyRef.new_ref(PyComplex(value), ctx.types.complex_type, None)

    def to_complex(self) -> complex:
        return self.value

    @pymethod(True)
    @staticmethod
    def i__complex__(zelf: PyRef[PyComplex], *, vm: VirtualMachine) -> PyRef[PyComplex]:
        if zelf.class_().is_(vm.ctx.types.complex_type):
            return zelf
        else:
            return PyComplex(zelf._.value).into_ref(vm)

    @pyproperty()
    def get_real(self, *, vm: VirtualMachine) -> PyObjectRef:
        return pyfloat.PyFloat.from_(self.value.real).into_ref(vm)

    @pyproperty()
    def get_imag(self, *, vm: VirtualMachine) -> PyObjectRef:
        return pyfloat.PyFloat.from_(self.value.imag).into_ref(vm)

    @pymethod(True)
    def i__abs__(self, *, vm: VirtualMachine) -> PyObjectRef:
        return pyfloat.PyFloat.from_(abs(self.value)).into_ref(vm)

    def op(
        self,
        other: PyObjectRef,
        op: Callable[[complex, complex], complex],
        vm: VirtualMachine,
    ) -> PyObjectRef:
        if (value := to_op_complex(other, vm)) is None:
            return vm.ctx.get_not_implemented()
        else:
            return PyComplex(op(self.value, value)).into_ref(vm)

    @pymethod(True)
    def i__add__(self, other: PyObjectRef, *, vm: VirtualMachine) -> PyObjectRef:
        return self.op(other, operator.add, vm)

    @pymethod(True)
    def i__radd__(self, other: PyObjectRef, *, vm: VirtualMachine) -> PyObjectRef:
        return self.op(other, operator.add, vm)

    @pymethod(True)
    def i__sub__(self, other: PyObjectRef, *, vm: VirtualMachine) -> PyObjectRef:
        return self.op(other, operator.sub, vm)

    @pymethod(True)
    def i__rsub__(self, other: PyObjectRef, *, vm: VirtualMachine) -> PyObjectRef:
        return self.op(other, lambda a, b: b - a, vm)

    @pymethod(True)
    def i__mul__(self, other: PyObjectRef, *, vm: VirtualMachine) -> PyObjectRef:
        return self.op(other, operator.mul, vm)

    @pymethod(True)
    def i__rmul__(self, other: PyObjectRef, *, vm: VirtualMachine) -> PyObjectRef:
        return self.op(other, operator.mul, vm)

    @pymethod(True)
    def i__truediv__(self, other: PyObjectRef, *, vm: VirtualMachine) -> PyObjectRef:
        return self.op(other, lambda a, b: inner_div(a, b, vm), vm)

    @pymethod(True)
    def i__rtruediv__(self, other: PyObjectRef, *, vm: VirtualMachine) -> PyObjectRef:
        return self.op(other, lambda a, b: inner_div(b, a, vm), vm)

    @pymethod(True)
    def conjugate(self, *, vm: VirtualMachine) -> PyObjectRef:
        return PyComplex(self.value.conjugate()).into_ref(vm)

    @pymethod(True)
    def i__pos__(self, *, vm: VirtualMachine) -> PyObjectRef:
        return PyComplex(self.value).into_ref(vm)

    @pymethod(True)
    def i__neg__(self, *, vm: VirtualMachine) -> PyObjectRef:
        return PyComplex(-self.value).into_ref(vm)

    @pymethod(True)
    def i__repr__(self, *, vm: VirtualMachine) -> PyObjectRef:
        return pystr.PyStr(repr(self.value)).into_ref(vm)

    @pymethod(True)
    def i__bool__(self, *, vm: VirtualMachine) -> PyObjectRef:
        return vm.ctx.new_bool(bool(self.value))

    @pymethod(True)
    def i__pow__(
        self,
        other: PyObjectRef,
        mod_val: Optional[PyObjectRef] = None,
        *,
        vm: VirtualMachine,
    ) -> PyObjectRef:
        if mod_val is not None:
            vm.new_value_error("complex modulo not allowed")
        return self.op(other, lambda a, b: inner_pow(a, b, vm), vm)

    @pymethod(True)
    def i__rpow__(self, other: PyObjectRef, *, vm: VirtualMachine) -> PyObjectRef:
        return self.op(other, lambda a, b: inner_pow(b, a, vm), vm)

    @pymethod(True)
    def i__getnewargs__(self, *, vm: VirtualMachine) -> PyObjectRef:
        return vm.new_tuple(
            [vm.ctx.new_float(self.value.real), vm.ctx.new_float(self.value.imag)]
        )

    @classmethod
    def py_new(
        cls, class_: PyTypeRef, fargs: fn.FuncArgs, vm: VirtualMachine
    ) -> PyObjectRef:
        args = fargs.bind(__py_new_args).arguments
        raise NotImplementedError

    @classmethod
    def cmp(
        cls,
        zelf: PyRef[PyComplex],
        other: PyObject,
        op: PyComparisonOp,
        vm: VirtualMachine,
    ) -> PyComparisonValue:
        def do() -> PyComparisonValue:
            if (value := other.payload_if_subclass(PyComplex, vm)) is not None:
                return PyComparisonValue(zelf._.value == value.value)
            else:
                try:
                    value = pyfloat.to_op_float(other, vm)
                except PyImplBase:
                    return PyComparisonValue(False)
                else:
                    if value is not None:
                        return PyComparisonValue(zelf._.value == value)
                    else:
                        return PyComparisonValue(None)

        return op.eq_only(do)

    @classmethod
    def hash(cls, zelf: PyRef[PyComplex], vm: VirtualMachine) -> PyHash:
        return hash(zelf._.value)


# TODO: impl PyObjectRef @ 41 : `try_complex(self, vm)`


def __py_new_args(
    real: Optional[PyObjectRef] = None, imag: Optional[PyObjectRef] = None
):
    ...


def to_op_complex(value: PyObjectRef, vm: VirtualMachine) -> Optional[complex]:
    if (complex_ := value.payload_if_subclass(PyComplex, vm)) is not None:
        return complex_.value
    else:
        r = pyfloat.to_op_float(value, vm)
        if r is None:
            return None
        return complex(r)


def inner_div(v1: complex, v2: complex, vm: VirtualMachine) -> complex:
    if v2 == 0:
        vm.new_zero_division_error("complex division by zero")
    return v1 / v2


def inner_pow(v1: complex, v2: complex, vm: VirtualMachine) -> complex:
    try:
        return v1**v2
    except ZeroDivisionError as _:
        vm.new_zero_division_error(
            f"{v1} cannot be raised to a negative or complex power"
        )
        # raise PyImplException.from_python_exception(e)
    except OverflowError as _:
        vm.new_overflow_error("complex exponentiation overflow")
        # raise PyImplException.from_python_exception(e)
    # else:
    # return PyComplex(ans).into_ref(vm)
    # if v1 == 0:
    #     if v2.imag != 0:
    #         vm.new_zero_division_error(
    #             f"{v1} cannot be raised to a negative or complex power"
    #         )
    #     elif v2 == 0:
    #         return PyComplex(1 + 0j).into_ref(vm)
    #     else:
    #         return PyComplex(0j).into_ref(vm)

    # ans = v1 ** v2
    # if False:
    #     # TOD?O: ans.is_infinite() && !(v1.is_infinite() || v2.is_infinite())
    #     vm.new_overflow_error("complex exponentiation overflow")
    # return PyComplex(ans).into_ref(vm)


# @derive_from_args
# @dataclass
# class ComplexArgs:
#     real: Optional[PyObjectRef]
#     imag: Optional[PyObjectRef]


def init(context: PyContext) -> None:
    PyComplex.extend_class(context, context.types.complex_type)
