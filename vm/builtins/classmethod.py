from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional
from common.error import PyImplBase

if TYPE_CHECKING:
    from vm.builtins.pytype import PyTypeRef
    from vm.function_ import FuncArgs
    from vm.pyobject import PyContext
    from vm.pyobjectrc import PyObjectRef, PyRef
    from vm.vm import VirtualMachine

import vm.pyobject as po
import vm.pyobjectrc as prc
import vm.types.slot as slot
import vm.builtins.function as pyfunction
from common.deco import pyproperty


@po.pyimpl(get_descriptor=True, constructor=True)
@po.pyclass("classmethod")
@dataclass
class PyClassMethod(po.PyClassImpl, slot.GetDescriptorMixin, slot.ConstructorMixin):
    callable: PyObjectRef

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.classmethod_type

    @staticmethod
    def new_ref(callable: PyObjectRef, ctx: PyContext) -> PyRef[PyClassMethod]:
        return prc.PyRef.new_ref(
            PyClassMethod(callable), ctx.types.classmethod_type, None
        )

    @staticmethod
    def descr_get(
        zelf: PyObjectRef,
        obj: Optional[PyObjectRef],
        cls: Optional[PyObjectRef],
        vm: VirtualMachine,
    ) -> PyObjectRef:
        zelf_, obj_ = PyClassMethod._unwrap(zelf, obj, vm)
        if cls is None:
            cls = obj_.clone_class().into_pyobj(vm)
        return pyfunction.PyBoundMethod.new_ref(cls, zelf_._.callable, vm.ctx)

    @classmethod
    def py_new(
        cls, class_: PyTypeRef, args: FuncArgs, vm: VirtualMachine
    ) -> PyObjectRef:
        return PyClassMethod(args.take_positional_arg()).into_pyresult_with_type(
            vm, class_
        )

    @pyproperty()
    def get_func(self) -> PyObjectRef:
        return self.callable

    @pyproperty()
    def get_isabstractmethod(self, vm: VirtualMachine) -> PyObjectRef:
        try:
            r = vm.get_attribute_opt(self.callable, vm.mk_str("__isabstractmethod__"))
        except PyImplBase as _:
            pass
        else:
            if r is not None:
                return r
        return vm.ctx.new_bool(False)

    @pyproperty()
    def set_isabstractmethod(self, value: PyObjectRef, vm: VirtualMachine) -> None:
        self.callable.set_attr(vm.mk_str("__isabstractmethod__"), value, vm)


def init(context: PyContext) -> None:
    PyClassMethod.extend_class(context, context.types.classmethod_type)
