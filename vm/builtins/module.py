from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING
from common.error import PyImplBase, PyImplErrorStr

if TYPE_CHECKING:
    from vm.builtins.dict import PyDictRef
    from vm.builtins.pystr import PyStrRef
    from vm.builtins.pytype import PyTypeRef
    from vm.function_ import FuncArgs
    from vm.pyobject import (
        PyClassImpl,
        PyContext,
        PyValueMixin,
        pyclass,
        pyimpl,
        tp_flags,
    )
    from vm.pyobjectrc import PyObjectRef, PyRef
    from vm.vm import VirtualMachine
import vm.pyobject as po


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl(get_attr=True)
@po.pyclass("module")
@dataclass
class PyModule(po.PyClassImpl, po.PyValueMixin):
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
        vm.new_attribute_error(f"module has no attribute '{name}'")

    # # FIXME?
    # def dict(self) -> PyDictRef:
    #     return self

    def init_module_dict(
        self, name: PyObjectRef, doc: PyObjectRef, vm: VirtualMachine
    ) -> None:
        dict_ = self.into_ref(vm).dict
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

    # TODO: impl PyModule @ 27
    # TODO: (inherit from mixin) impl GetAttr for PyModule


def init(context: PyContext) -> None:
    PyModule.extend_class(context, context.types.module_type)
