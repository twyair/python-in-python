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
import vm.pyobject as po
import vm.types.slot as slot

# import vm.function_ as fn


@po.pyimpl(constructor=True)
@po.pyclass("bool", base="PyInt")
@dataclass
class PyBool(
    po.PyClassImpl,
    po.PyValueMixin,
    po.TryFromObjectMixin,
    slot.ConstructorMixin,
):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.bool_type

    # TODO: impl PyBool @ 114

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
    r = obj.payload_(PyInt)
    assert r is not None
    return r


def init(context: PyContext) -> None:
    PyBool.extend_class(context, context.types.bool_type)
