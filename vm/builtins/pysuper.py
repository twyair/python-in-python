from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional
from common.deco import pymethod
from vm import extend_class

if TYPE_CHECKING:
    from vm.pyobject import PyContext
    from vm.pyobjectrc import PyObjectRef, PyRef
    from vm.builtins.pytype import PyType, PyTypeRef
    from vm.vm import VirtualMachine

import vm.pyobject as po
import vm.function_ as fn
import vm.types.slot as slot
import vm.builtins.pystr as pystr

from common.error import PyImplBase


@po.pyimpl(constructor=True, get_descriptor=True, get_attr=True)
@po.pyclass("super")
@dataclass
class PySuper(
    po.PyClassImpl,
    slot.ConstructorMixin,
    slot.GetAttrMixin,
    slot.GetDescriptorMixin,
):
    type: PyTypeRef
    obj: Optional[tuple[PyObjectRef, PyTypeRef]]

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.super_type

    @staticmethod
    def new(typ: PyTypeRef, obj: PyObjectRef, vm: VirtualMachine) -> PySuper:
        if vm.is_none(obj):
            v = None
        else:
            v = (obj, supercheck(typ, obj, vm))
        return PySuper(typ, v)

    @pymethod(True)
    def i__repr__(self, *, vm: VirtualMachine) -> str:
        typname = self.type._.name()
        if self.obj is not None:
            return f"<super: <class '{typname}'>, <{self.obj[1]._.name()} object>>"
        else:
            return f"<super: <class '{typname}'>, NULL>"

    @classmethod
    def py_new(
        cls, class_: PyTypeRef, args: fn.FuncArgs, /, vm: VirtualMachine
    ) -> PyObjectRef:
        raise NotImplementedError

    @classmethod
    def getattro(
        cls, zelf: PyRef[PySuper], name: pystr.PyStrRef, vm: VirtualMachine
    ) -> PyObjectRef:
        raise NotImplementedError

    @classmethod
    def descr_get(
        cls,
        zelf: PyObjectRef,
        obj: Optional[PyObjectRef],
        class_: Optional[PyObjectRef],
        vm: VirtualMachine,
    ) -> PyObjectRef:
        raise NotImplementedError


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

    extend_class(
        context,
        context.types.super_type,
        {
            "__doc__": context.new_str(
                "super() -> same as super(__class__, <first argument>)\nsuper(type) -> unbound super object\nsuper(type, obj) -> bound super object; requires isinstance(obj, type)\nsuper(type, type2) -> bound super object; requires issubclass(type2, type)\nTypical use to call a cooperative superclass method:\nclass C(B):\n    def meth(self, arg):\n        super().meth(arg)\nThis works for class methods too:\nclass C(B):\n    @classmethod\n    def cmeth(cls, arg):\n        super().cmeth(arg)\n"
            )
        },
    )
