from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional
from common.deco import pymethod, pyproperty, pyslot
from common.error import PyImplBase
from vm import extend_class

if TYPE_CHECKING:
    from vm.builtins.pytype import PyTypeRef
    from vm.pyobject import PyContext
    from vm.pyobjectrc import PyObjectRef, PyRef
    from vm.vm import VirtualMachine
import vm.pyobject as po
import vm.pyobjectrc as prc
import vm.function_ as fn
import vm.types.slot as slot
from common import to_opt


@po.tp_flags(basetype=True)
@po.pyimpl(get_descriptor=True)
@po.pyclass("property")
@dataclass
class PyProperty(po.PyClassImpl, slot.GetDescriptorMixin):
    getter: Optional[PyObjectRef]
    setter: Optional[PyObjectRef]
    deleter: Optional[PyObjectRef]
    doc: Optional[PyObjectRef]

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.property_type

    @pyslot
    @staticmethod
    def slot_new(
        class_: PyTypeRef, fargs: fn.FuncArgs, vm: VirtualMachine
    ) -> PyObjectRef:
        return PyProperty(None, None, None, None).into_pyresult_with_type(vm, class_)

    @pymethod(False)
    def i__init__(self, fargs: fn.FuncArgs, *, vm: VirtualMachine) -> None:
        args = fargs.bind(f__init_args).arguments
        self.getter = args["fget"]
        self.setter = args["fset"]
        self.deleter = args["fdel"]
        self.doc = args["doc"]

    @pyslot
    @staticmethod
    def slot_descr_set(
        zelf: PyObjectRef,
        obj: PyObjectRef,
        value: Optional[PyObjectRef],
        vm: VirtualMachine,
    ) -> None:
        zelf_ = prc.PyRef.try_from_object(PyProperty, vm, zelf)._
        if value is not None:
            if zelf_.setter is not None:
                vm.invoke(zelf_.setter, fn.FuncArgs([obj, value]))
            else:
                vm.new_attribute_error("can't set attribute")
        else:
            if zelf_.deleter is not None:
                vm.invoke(zelf_.deleter, fn.FuncArgs([obj]))
            else:
                vm.new_attribute_error("can't delete attribute")

    @pymethod(True)
    @staticmethod
    def i__set__(
        zelf: PyObjectRef,
        obj: PyObjectRef,
        value: PyObjectRef,
        /,
        *,
        vm: VirtualMachine,
    ) -> None:
        PyProperty.slot_descr_set(zelf, obj, value, vm)

    @pymethod(True)
    @staticmethod
    def i__delete__(
        zelf: PyObjectRef, obj: PyObjectRef, /, *, vm: VirtualMachine
    ) -> None:
        PyProperty.slot_descr_set(zelf, obj, None, vm)

    @pyproperty()
    def get_fget(self, *, vm: VirtualMachine) -> Optional[PyObjectRef]:
        return self.getter

    @pyproperty()
    def get_fset(self, *, vm: VirtualMachine) -> Optional[PyObjectRef]:
        return self.setter

    @pyproperty()
    def get_fdel(self, *, vm: VirtualMachine) -> Optional[PyObjectRef]:
        return self.deleter

    @staticmethod
    def doc_getter(vm: VirtualMachine, zelf: PyRef[PyProperty]) -> PyObjectRef:
        if zelf._.doc is None:
            return vm.ctx.get_none()
        else:
            return zelf._.doc

    @staticmethod
    def doc_setter(
        vm: VirtualMachine, zelf: PyRef[PyProperty], value: Optional[PyObjectRef]
    ) -> None:
        zelf._.doc = value

    @pymethod(True)
    @staticmethod
    def r__getter__(
        zelf: PyRef[PyProperty], getter: Optional[PyObjectRef], *, vm: VirtualMachine
    ) -> PyRef[PyProperty]:
        return PyProperty(
            getter=getter or zelf._.get_fget(vm=vm),
            setter=zelf._.get_fset(vm=vm),
            deleter=zelf._.get_fdel(vm=vm),
            doc=None,
        ).into_ref_with_type(vm, zelf.clone_class())

    @pymethod(True)
    @staticmethod
    def r__setter__(
        zelf: PyRef[PyProperty], setter: Optional[PyObjectRef], *, vm: VirtualMachine
    ) -> PyRef[PyProperty]:
        return PyProperty(
            getter=zelf._.get_fget(vm=vm),
            setter=setter or zelf._.get_fset(vm=vm),
            deleter=zelf._.get_fdel(vm=vm),
            doc=None,
        ).into_ref_with_type(vm, zelf.clone_class())

    @pymethod(True)
    @staticmethod
    def r__deleter__(
        zelf: PyRef[PyProperty], deleter: Optional[PyObjectRef], *, vm: VirtualMachine
    ) -> PyRef[PyProperty]:
        return PyProperty(
            getter=zelf._.get_fget(vm=vm),
            setter=zelf._.get_fset(vm=vm),
            deleter=deleter or zelf._.get_fdel(vm=vm),
            doc=None,
        ).into_ref_with_type(vm, zelf.clone_class())

    @pyproperty()
    def get___isabstractmethod__(self, *, vm: VirtualMachine) -> PyObjectRef:
        if self.getter is not None:
            g = self.getter
            getter_abstract = to_opt(
                lambda: g.get_attr(vm.ctx.new_str("__isabstractmethod__"), vm)
            ) or vm.ctx.new_bool(False)
        else:
            getter_abstract = vm.ctx.new_bool(False)
        if self.setter is not None:
            g = self.setter
            setter_abstract = to_opt(
                lambda: g.get_attr(vm.ctx.new_str("__isabstractmethod__"), vm)
            ) or vm.ctx.new_bool(False)
        else:
            setter_abstract = vm.ctx.new_bool(False)
        return to_opt(
            lambda: vm._or(setter_abstract, getter_abstract)
        ) or vm.ctx.new_bool(False)

    @pyproperty()
    def set___isabstractmethod__(
        self, value: PyObjectRef, *, vm: VirtualMachine
    ) -> None:
        if self.getter is not None:
            self.getter.set_attr(vm.ctx.new_str("__isabstractmethod__"), value, vm)

    @classmethod
    def descr_get(
        cls,
        zelf: PyObjectRef,
        obj: Optional[PyObjectRef],
        class_: Optional[PyObjectRef],
        vm: VirtualMachine,
    ) -> PyObjectRef:
        zelf, obj = PyProperty._unwrap(zelf, obj, vm)
        if vm.is_none(obj):
            return zelf
        elif zelf._.getter is not None:
            return vm.invoke(zelf._.getter, fn.FuncArgs([obj]))
        else:
            vm.new_attribute_error("unreadable attribute")


def f__init_args(
    fget: Optional[PyObjectRef] = None,
    fset: Optional[PyObjectRef] = None,
    fdel: Optional[PyObjectRef] = None,
    doc: Optional[PyObjectRef] = None,
):
    ...


def init(context: PyContext) -> None:
    PyProperty.extend_class(context, context.types.property_type)
    extend_class(
        context,
        context.types.property_type,
        {
            "__doc__": context.new_getset(
                "__doc__",
                context.types.property_type,
                PyProperty.doc_getter,
                PyProperty.doc_setter,
            )
        },
    )
