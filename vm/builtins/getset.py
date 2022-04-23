from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Optional, TypeAlias
from common.error import PyImplError

if TYPE_CHECKING:
    from vm.builtins.pytype import PyTypeRef
    from vm.pyobject import PyContext
    from vm.pyobjectrc import PyObjectRef
    from vm.vm import VirtualMachine
import vm.pyobject as po
import vm.types.slot as slot

# TODO: impl IntoPyGetterFunc, ...

PyGetterFunc: TypeAlias = Callable[["VirtualMachine", "PyObjectRef"], "PyObjectRef"]
PySetterFunc: TypeAlias = Callable[
    ["VirtualMachine", "PyObjectRef", "PyObjectRef"], None
]
PyDeleterFunc: TypeAlias = Callable[["VirtualMachine", "PyObjectRef"], None]


@po.pyimpl(get_descriptor=True, constructor=False)
@po.pyclass("getset_descriptor")
@dataclass
class PyGetSet(po.PyClassImpl, slot.GetDescriptorMixin):
    name: str
    klass: PyTypeRef
    getter: Optional[PyGetterFunc]
    setter: Optional[PySetterFunc]
    deleter: Optional[PyDeleterFunc]

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.getset_type

    @staticmethod
    def new(name: str, class_: PyTypeRef) -> PyGetSet:
        return PyGetSet(name, class_, None, None, None)

    def with_get(self, getter: PyGetterFunc) -> PyGetSet:
        self.getter = getter
        return self

    def with_set(self, setter: PySetterFunc) -> PyGetSet:
        self.setter = setter
        return self

    def with_delete(self, deleter: PyDeleterFunc) -> PyGetSet:
        self.deleter = deleter
        return self

    @classmethod
    def descr_get(
        cls,
        zelf: PyObjectRef,
        obj: Optional[PyObjectRef],
        class_: Optional[PyObjectRef],
        vm: VirtualMachine,
    ) -> PyObjectRef:
        # assert False, (zelf._.name, type(zelf._), cls, type(obj))
        try:
            zelf_, obj_ = cls._check(zelf, obj, vm)
        except PyImplError as err:
            return err.obj
        if (f := zelf_._.getter) is not None:
            return f(vm, obj_)
        else:
            vm.new_attribute_error(
                "attribute '{}' of '{}' objects is not readable".format(
                    zelf_._.name, cls.class_(vm)._.name()
                )
            )


def init(context: PyContext) -> None:
    PyGetSet.extend_class(context, context.types.getset_type)
