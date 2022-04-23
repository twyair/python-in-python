from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Generic, Optional, Set, TypeVar, Union


if TYPE_CHECKING:
    from vm.builtins.dict import PyDict, PyDictRef
    from vm.protocol.mapping import PyMapping, PyMappingMethods
    from vm.pyobjectrc import PyObjectRef, PyRef
    from vm.types.slot import IterFunc
    from vm.vm import VirtualMachine
    from vm.protocol.iter import PyIterIter
    from vm.function_ import FuncArgs


import vm.builtins.iter as pyiter
import vm.builtins.dict as pydict
import vm.protocol.iter as vm_iter
import vm.protocol.mapping as mapping

# from vm.protocol.iter import PyIter


@dataclass
class ArgCallable:
    obj: PyObjectRef

    @staticmethod
    def try_from_object(vm: VirtualMachine, obj: PyObjectRef) -> ArgCallable:
        if vm.is_callable(obj):
            return ArgCallable(obj)
        else:
            vm.new_type_error(f"'{obj.class_()._.name()}' object is not callable")

    def invoke(self, args: FuncArgs, vm: VirtualMachine) -> PyObjectRef:
        return vm.invoke(self.obj, args)


T = TypeVar("T")


# TODO
# @dataclass
# class OptionalArg(Generic[T]):
#     value: Optional[T]

#     @staticmethod
#     def try_from_object(vm: VirtualMachine, obj: PyObjectRef) -> OptionalArg:
#         pass


@dataclass
class ArgIterable(Generic[T]):
    iterable: PyObjectRef
    iterfn: Optional[IterFunc]

    @staticmethod
    def try_from_object(vm: VirtualMachine, obj: PyObjectRef) -> ArgIterable:
        cls = obj.class_()
        iterfn = cls._.mro_find_map(lambda x: x.slots.iter)
        if iterfn is None and not cls._.has_attr("__getitem__"):
            vm.new_type_error(f"'{cls._.name()}' object is not iterable")
        return ArgIterable(obj, iterfn)

    def iter(self, vm: VirtualMachine) -> PyIterIter[PyObjectRef]:
        if self.iterfn is not None:
            return vm_iter.PyIter(self.iterfn(self.iterable, vm), None).into_iter(vm)
        else:
            return vm_iter.PyIter(
                pyiter.PySequenceIterator.new(self.iterable, vm).into_object(vm), None
            ).into_iter(vm)


@dataclass
class ArgMapping:
    obj: PyObjectRef
    mapping_methods: PyMappingMethods

    @staticmethod
    def from_dict_exact(dict: PyDictRef) -> ArgMapping:
        return ArgMapping(
            obj=dict,
            mapping_methods=pydict.PyDict.MAPPING_METHODS,
        )

    @staticmethod
    def try_from_object(vm: VirtualMachine, obj: PyObjectRef) -> ArgMapping:
        return ArgMapping(obj, mapping.PyMapping.try_protocol(obj, vm).methods_(vm))

    def mapping(self) -> PyMapping:
        return mapping.PyMapping.with_methods(self.obj, self.mapping_methods)

    def into_object(self) -> PyObjectRef:
        return self.obj
