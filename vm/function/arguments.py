from __future__ import annotations
from dataclasses import dataclass
from typing import Generic, Optional, Set, TypeVar, Union
from vm.builtins.dict import PyDict, PyDictRef
from vm.protocol.mapping import PyMapping, PyMappingMethods
from vm.pyobjectrc import PyObjectRef, PyRef
from vm.types.slot import IterFunc


@dataclass
class ArgCallable:
    obj: PyObjectRef


T = TypeVar("T")


@dataclass
class ArgIterable(Generic[T]):
    iterable: PyObjectRef
    iterfn: Optional[IterFunc]


@dataclass
class ArgMapping:
    obj: PyObjectRef
    mapping_methods: PyMappingMethods

    @staticmethod
    def from_dict_exact(dict: PyDictRef) -> ArgMapping:
        return ArgMapping(
            obj=dict,
            mapping_methods=PyDict.MAPPING_METHODS,
        )

    def mapping(self) -> PyMapping:
        return PyMapping.with_methods(self.obj, self.mapping_methods)
