from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from vm.pyobject import PyContext
    from vm.pyobjectrc import PyObjectRef
    from typing import Union
    from vm.builtins.pytype import PyTypeRef
    from vm.vm import VirtualMachine
import vm.pyobject as po


@po.pyimpl(constructor=True, iterable=True, as_mapping=True, as_sequence=True)
@po.pyclass("mappingproxy")
@dataclass
class PyMappingProxy(po.PyClassImpl):
    mapping: MappingProxyInner

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.mappingproxy_type

    @staticmethod
    def new(class_: PyTypeRef) -> PyMappingProxy:
        return PyMappingProxy(MappingProxyClass(class_))

    # TODO: impl Constructor for PyMappingProxy
    # TODO: impl PyMappingProxy @ 61
    # TODO: impl AsMapping for PyMappingProxy
    # TODO: impl AsSequence for PyMappingProxy
    # TODO: impl Iterable for PyMappingProxy


@dataclass
class MappingProxyClass:
    value: PyTypeRef


@dataclass
class MappingProxyDict:
    value: PyObjectRef


MappingProxyInner = Union[MappingProxyClass, MappingProxyDict]


def init(context: PyContext) -> None:
    PyMappingProxy.extend_class(context, context.types.mappingproxy_type)
