from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from vm.builtins.int import PyInt
    from vm.builtins.pytype import PyTypeRef
    from vm.pyobject import PyContext
    from vm.pyobjectrc import PyObject, PyObjectRef
    from vm.vm import VirtualMachine
    from vm.function_ import FuncArgs
    from vm.builtins.pystr import PyStrRef
import vm.pyobject as po
import vm.types.slot as slot
import vm.builtins.int as pyint
from common.deco import pymethod


@po.pyimpl(constructor=True)
@po.pyclass("bool", base="PyInt")
@dataclass
class PyBool(po.PyClassImpl, slot.ConstructorMixin):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.bool_type

    @classmethod
    def static_baseclass(cls) -> PyTypeRef:
        return pyint.PyInt.static_type()

    @pymethod(True)
    @staticmethod
    def i__repr__(zelf: PyObjectRef, *, vm: VirtualMachine) -> str:
        return repr(try_from_borrowed_object(vm, zelf))

    @pymethod(True)
    @staticmethod
    def format(
        zelf: PyObjectRef, format_spec: PyStrRef, *, vm: VirtualMachine
    ) -> PyStrRef:
        if not format_spec._.as_str():
            return zelf.str(vm)
        else:
            vm.new_type_error("unsupported format string passed to bool.__format__")

    @pymethod(True)
    @staticmethod
    def i__or__(
        zelf: PyObjectRef, rhs: PyObjectRef, *, vm: VirtualMachine
    ) -> po.PyArithmeticValue[int]:
        if zelf.isinstance(vm.ctx.types.bool_type) and rhs.isinstance(
            vm.ctx.types.bool_type
        ):
            return po.PyArithmeticValue(int(get_value(zelf) or get_value(rhs)))
        else:
            return get_py_int(zelf).i__or__(rhs, vm=vm)

    @pymethod(True)
    @staticmethod
    def i__ror__(
        zelf: PyObjectRef, rhs: PyObjectRef, *, vm: VirtualMachine
    ) -> po.PyArithmeticValue[int]:
        return PyBool.i__or__(zelf, rhs, vm=vm)

    @pymethod(True)
    @staticmethod
    def i__and__(
        zelf: PyObjectRef, rhs: PyObjectRef, *, vm: VirtualMachine
    ) -> po.PyArithmeticValue[int]:
        if zelf.isinstance(vm.ctx.types.bool_type) and rhs.isinstance(
            vm.ctx.types.bool_type
        ):
            return po.PyArithmeticValue(int(get_value(zelf) and get_value(rhs)))
        else:
            return get_py_int(zelf).i__and__(rhs, vm=vm)

    @pymethod(True)
    @staticmethod
    def i__rand__(
        zelf: PyObjectRef, rhs: PyObjectRef, *, vm: VirtualMachine
    ) -> po.PyArithmeticValue[int]:
        return PyBool.i__and__(zelf, rhs, vm=vm)

    @pymethod(True)
    @staticmethod
    def i__xor__(
        zelf: PyObjectRef, rhs: PyObjectRef, *, vm: VirtualMachine
    ) -> po.PyArithmeticValue[int]:
        if zelf.isinstance(vm.ctx.types.bool_type) and rhs.isinstance(
            vm.ctx.types.bool_type
        ):
            return po.PyArithmeticValue(int(get_value(zelf) ^ get_value(rhs)))
        else:
            return get_py_int(zelf).i__xor__(rhs, vm=vm)

    @pymethod(True)
    @staticmethod
    def i__rxor__(
        zelf: PyObjectRef, rhs: PyObjectRef, *, vm: VirtualMachine
    ) -> po.PyArithmeticValue[int]:
        return PyBool.i__xor__(zelf, rhs, vm=vm)

    @classmethod
    def py_new(
        cls, class_: PyTypeRef, fargs: FuncArgs, vm: VirtualMachine
    ) -> PyObjectRef:

        if not class_.isinstance(vm.ctx.types.type_type):
            actual_type = class_.class_()._.name()
            vm.new_type_error(
                f"requires a 'type' object but received a '{actual_type}'"
            )

        arg = fargs.take_positional_optional(
            lambda: vm.new_type_error("wrong args")  # TODO: imrpove error msg
        )
        if arg is None:
            val = False
        else:
            val = arg.try_to_bool(vm)

        return vm.ctx.new_bool(val)


def get_value(obj: PyObject) -> bool:
    return get_py_int(obj).as_int() != 0


def get_py_int(obj: PyObject) -> PyInt:
    r = obj.payload_(pyint.PyInt)
    assert r is not None
    return r


def bool_to_pyobject(v: bool) -> PyObjectRef:
    raise NotImplementedError


def try_from_borrowed_object(vm: VirtualMachine, obj: PyObjectRef) -> bool:
    if obj.isinstance(vm.ctx.types.int_type):
        return get_value(obj)
    else:
        vm.new_type_error(f"Expected type bool, not {obj.class_()._.name()}")


def init(context: PyContext) -> None:
    PyBool.extend_class(context, context.types.bool_type)
