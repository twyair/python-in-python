from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Optional, TypeAlias

if TYPE_CHECKING:
    from vm.builtins.pytype import PyTypeRef
    from vm.pyobject import PyContext
    from vm.pyobjectrc import PyObjectRef
    from vm.vm import VirtualMachine
import vm.pyobject as po

# TODO: impl IntoPyGetterFunc, ...

# TODO: py_dyn_fn!(...)
PyGetterFunc: TypeAlias = Callable[["VirtualMachine", "PyObjectRef"], "PyObjectRef"]
PySetterFunc: TypeAlias = Callable[
    ["VirtualMachine", "PyObjectRef", "PyObjectRef"], None
]
PyDeleterFunc: TypeAlias = Callable[["VirtualMachine", "PyObjectRef"], None]


@po.pyimpl(get_descriptor=True, constructor=True)
@po.pyclass("getset_descriptor")
@dataclass
class PyGetSet(po.PyClassImpl):
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

    # TODO: impl GetDescriptor for PyGetSet
    # TODO? impl Unconstructible for PyGetSet


def init(context: PyContext) -> None:
    PyGetSet.extend_class(context, context.types.getset_type)
