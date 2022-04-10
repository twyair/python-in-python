from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional
if TYPE_CHECKING:
    from vm.builtins.int import PyInt
    from vm.builtins.pytype import PyTypeRef
    from vm.pyobject import PyClassImpl, PyContext, PyValueMixin, pyclass, pyimpl
    from vm.pyobjectrc import PyObject, PyObjectRef, PyRef
    from vm.vm import VirtualMachine
import vm.pyobject as po

@po.pyimpl(constructor=True)
@po.pyclass("bool", base="PyInt")  # FIXME?
@dataclass
class PyBool(po.PyClassImpl, po.PyValueMixin):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.bool_type

    # TODO: impl PyBool @ 114


def get_value(obj: PyObject) -> bool:
    return obj.payload_(PyInt).as_int() != 0


def get_py_int(obj: PyObject) -> PyInt:
    return obj.payload_(PyInt)


def init(context: PyContext) -> None:
    PyBool.extend_class(context, context.types.bool_type)
