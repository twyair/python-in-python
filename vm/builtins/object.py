from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional
from common.error import PyImplBase
if TYPE_CHECKING:
    from vm.builtins.dict import PyDictRef
    from vm.builtins.pystr import PyStrRef
    from vm.builtins.pytype import PyTypeRef
    from vm.pyobject import PyClassImpl, PyContext, PyValueMixin, pyclass, pyimpl, tp_flags
    from vm.pyobjectrc import PyObject, PyObjectRef, PyRef
    from vm.vm import VirtualMachine
import vm.pyobject as po

@po.tp_flags(basetype=True)
@po.pyimpl()
@po.pyclass("object")
@dataclass
class PyBaseObject(po.PyClassImpl, po.PyValueMixin):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.object_type

    # TODO: impl PyBaseObject @ 27


def object_get_dict(obj: PyObjectRef, vm: VirtualMachine) -> PyDictRef:
    if obj.dict is not None:
        return obj.dict.d
    else:
        vm.new_attribute_error("This object has no __dict__")


def object_set_dict(obj: PyObjectRef, dict: PyDictRef, vm: VirtualMachine) -> None:
    try:
        obj.set_dict(dict)
    except PyImplBase as _:
        vm.new_attribute_error("This object has no __dict__")


def generic_getattr(
    obj: PyObjectRef, attr_name: PyStrRef, vm: VirtualMachine
) -> PyObjectRef:
    return vm.generic_getattribute(obj, attr_name)


# TODO:
# def generic_setattr(
#     obj: PyObject, attr_name: PyStrRef, value: Optional[PyObjectRef], vm: VirtualMachine
# ) -> None:


# TODO:
# def common_reduce(obj: PyObjectRef, proto: int, vm: VirtualMachine) -> PyObjectRef:


def init(ctx: PyContext) -> None:
    PyBaseObject.extend_class(ctx, ctx.types.object_type)
