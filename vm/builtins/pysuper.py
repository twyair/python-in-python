from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, Union
from common.error import PyImplBase

if TYPE_CHECKING:
    from vm.pyobject import PyContext
    from vm.pyobjectrc import PyObjectRef, PyRef
    from vm.builtins.pytype import PyType, PyTypeRef
    from vm.vm import VirtualMachine
import vm.pyobject as po


@po.pyimpl(constructor=True, get_descriptor=True, get_attr=True)
@po.pyclass("super")
@dataclass
class PySuper(po.PyClassImpl):
    type: PyTypeRef
    obj: Optional[tuple[PyObjectRef, PyTypeRef]]

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.super_type

    # TODO: impl Constructor for PySuper
    # TODO: impl PySuper @ 99
    # TODO: impl GetAttr for PySuper
    # TODO: impl GetDescriptor for PySuper


def supercheck(ty: PyTypeRef, obj: PyObjectRef, vm: VirtualMachine) -> PyTypeRef:
    try:
        cls = obj.downcast(PyType)
    except PyImplBase as _:
        pass
    else:
        if cls._.issubclass(ty):
            return cls

    if obj.isinstance(ty):
        return obj.clone_class()

    class_attr = obj.get_attr(vm.mk_str("__class__"), vm)
    try:
        cls = class_attr.downcast(PyType)
    except PyImplBase as _:
        pass
    else:
        if not cls.is_(ty) and cls._.issubclass(ty):
            return cls

    vm.new_type_error("super(type, obj): obj must be an instance or subtype of type")


def init(context: PyContext) -> None:
    PySuper.extend_class(context, context.types.super_type)

    # TODO: extend_class!(context, super_type, {
