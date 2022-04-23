from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional
from common.deco import pymethod
from common.error import PyImplBase, PyImplErrorStr

if TYPE_CHECKING:
    from vm.builtins.pystr import PyStrRef
    from vm.builtins.pytype import PyTypeRef
    from vm.function_ import FuncArgs
    from vm.pyobject import PyContext
    from vm.pyobjectrc import PyObjectRef, PyRef
    from vm.vm import VirtualMachine
import vm.pyobject as po
import vm.types.slot as slot
import vm.builtins.pystr as pystr
import vm.builtins.list as pylist
import vm.function_ as fn


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl(get_attr=True)
@po.pyclass("module")
@dataclass
class PyModule(po.PyClassImpl, slot.GetAttrMixin):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.module_type

    def get_attr(
        self: PyModule, attr_name: PyStrRef, vm: VirtualMachine
    ) -> PyObjectRef:
        return PyModule.getattr_inner(self.into_ref(vm), attr_name, vm)

    @staticmethod
    def getattr_inner(
        zelf: PyRef[PyModule], name: PyStrRef, vm: VirtualMachine
    ) -> PyObjectRef:
        if (attr := vm.generic_getattribute_opt(zelf, name, None)) is not None:
            return attr
        if zelf.dict is not None:
            try:
                getattr_ = zelf.dict.d.get_item(vm.mk_str("__getattr__"), vm)
                return vm.invoke(getattr_, FuncArgs([name]))
            except:
                pass
        vm.new_attribute_error(f"module has no attribute '{name._.as_str()}'")

    # # FIXME?
    # def dict(self) -> PyDictRef:
    #     return self

    @staticmethod
    def init_module_dict(
        zelf: PyRef[PyModule], name: PyObjectRef, doc: PyObjectRef, vm: VirtualMachine
    ) -> None:
        dict_ = zelf.dict
        assert dict_ is not None
        for attr, value in [
            ("name", name),
            ("doc", doc),
            ("package", vm.ctx.get_none()),
            ("loader", vm.ctx.get_none()),
            ("spec", vm.ctx.get_none()),
        ]:
            try:
                dict_.set_item(vm.mk_str(f"__{attr}__"), value, vm)
            except PyImplBase:
                raise PyImplErrorStr(f"Failed to set __{attr}__ on module")

    def set_attr(
        self, attr_name: PyStrRef, attr_value: PyObjectRef, vm: VirtualMachine
    ) -> None:
        self.set_attr(attr_name, attr_value, vm)

    @staticmethod
    def getattro(
        zelf: PyRef[PyModule], name: PyStrRef, vm: VirtualMachine
    ) -> PyObjectRef:
        return PyModule.getattr_inner(zelf, name, vm)

    @staticmethod
    def slot_new(class_: PyTypeRef, fargs: FuncArgs, vm: VirtualMachine) -> PyObjectRef:
        return PyModule().into_pyresult_with_type(vm, class_)

    @pymethod(False)
    @staticmethod
    def i__init__(
        zelf: PyRef[PyModule], fargs: FuncArgs, *, vm: VirtualMachine
    ) -> None:
        args = fargs.bind(args__init__).arguments
        PyModule.init_module_dict(
            zelf, args["name"], vm.unwrap_or_none(args["doc"]), vm
        )

    @staticmethod
    def name_(zelf: PyRef[PyModule], vm: VirtualMachine) -> Optional[PyStrRef]:
        v = vm.generic_getattribute_opt(zelf, vm.ctx.new_str("__name__"), None)
        if v is None:
            return None
        else:
            return v.downcast_ref(pystr.PyStr)

    @pymethod(True)
    @staticmethod
    def i__repr__(zelf: PyRef[PyModule], *, vm: VirtualMachine) -> PyObjectRef:
        importlib = vm.import_(vm.ctx.new_str("_frozen_importlib"), None, 0)
        module_repr = importlib.get_attr(vm.ctx.new_str("_module_repr"), vm)
        return vm.invoke(module_repr, fn.FuncArgs([zelf]))

    @pymethod(True)
    @staticmethod
    def i__dir__(zelf: PyRef[PyModule], *, vm: VirtualMachine) -> pylist.PyListRef:
        dict_ = zelf.dict_()
        if dict_ is None:
            vm.new_value_error("module has no dict")
        return vm.ctx.new_list(dict_._.entries.keys())


def args__init__(name: PyObjectRef, doc: Optional[PyObjectRef] = None):
    ...


def init(context: PyContext) -> None:
    PyModule.extend_class(context, context.types.module_type)
