from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Optional

if TYPE_CHECKING:
    from vm.function_ import FuncArgs
    from vm.pyobjectrc import PyObject, PyObjectRef
    from vm.vm import VirtualMachine


import vm.builtins.dict as dict_


@dataclass
class PyMappingMethods:
    length: Optional[Callable[[PyMapping, VirtualMachine], int]] = None
    subscript: Optional[
        Callable[[PyMapping, PyObject, VirtualMachine], PyObjectRef]
    ] = None
    ass_subscript: Optional[
        Callable[[PyMapping, PyObject, Optional[PyObjectRef], VirtualMachine], None]
    ] = None


@dataclass
class PyMapping:
    obj: PyObject
    methods: Optional[PyMappingMethods]

    @staticmethod
    def from_pyobj(obj: PyObject) -> PyMapping:
        return PyMapping(obj, None)

    @staticmethod
    def with_methods(obj: PyObject, methods: PyMappingMethods) -> PyMapping:
        return PyMapping(obj, methods)

    @staticmethod
    def try_protocol(obj: PyObject, vm: VirtualMachine) -> PyMapping:
        zelf = PyMapping.from_pyobj(obj)
        if zelf.check(vm):
            return zelf
        else:
            vm.new_type_error(f"{zelf.obj.class_()} is not a mapping object")

    def as_ref(self) -> PyObject:
        return self.obj

    def check(self, vm: VirtualMachine) -> bool:
        return self.methods_(vm).subscript is not None

    def methods_(self, vm: VirtualMachine) -> PyMappingMethods:
        if self.methods is not None:
            return self.methods
        if (
            f := self.obj.class_().payload.mro_find_map(
                lambda cls: cls.slots.as_mapping
            )
        ) is not None:
            self.methods = f(self.obj, vm)
        else:
            self.methods = PyMappingMethods()
        return self.methods

    def length_opt(self, vm: VirtualMachine) -> Optional[int]:
        f = self.methods_(vm).length
        if f is not None:
            return f(self, vm)
        return None

    def length_(self, vm: VirtualMachine) -> int:
        n = self.length_opt(vm)
        if n is not None:
            return n
        else:
            vm.new_type_error(
                f"object of type '{self.obj.class_()}' has no len() or not a mapping"
            )

    def subscript_(self, needle: PyObject, vm: VirtualMachine) -> PyObjectRef:
        f = self.methods_(vm).subscript
        if f is None:
            vm.new_type_error(f"{self.obj.class_()} is not a mapping")
        return f(self, needle, vm)

    def ass_subscript_(
        self, needle: PyObject, value: Optional[PyObjectRef], vm: VirtualMachine
    ) -> None:
        f = self.methods_(vm).ass_subscript
        if f is None:
            vm.new_type_error(
                f"'{self.obj.class_()}' object does not support item assignment"
            )
        return f(self, needle, value, vm)

    def keys(self, vm: VirtualMachine) -> PyObjectRef:
        if (dict := self.obj.downcast_ref_if_exact(dict_.PyDict, vm)) is not None:
            return dict_.PyDictKeys.new(dict).into_pyresult(vm)
        else:
            return self.method_output_as_list("keys", vm)

    def values(self, vm: VirtualMachine) -> PyObjectRef:
        if (dict := self.obj.downcast_ref_if_exact(dict_.PyDict, vm)) is not None:
            return dict_.PyDictValues.new(dict).into_pyresult(vm)
        else:
            return self.method_output_as_list("values", vm)

    def items(self, vm: VirtualMachine) -> PyObjectRef:
        if (dict := self.obj.downcast_ref_if_exact(dict_.PyDict, vm)) is not None:
            return dict_.PyDictItems.new(dict).into_pyresult(vm)
        else:
            return self.method_output_as_list("items", vm)

    def method_output_as_list(
        self, method_name: str, vm: VirtualMachine
    ) -> PyObjectRef:
        meth_output = vm.call_method(self.obj, method_name, FuncArgs.empty())
        if meth_output.is_(vm.ctx.types.list_type):
            return meth_output

        iter = meth_output.get_iter(vm)

        return vm.ctx.new_list(
            vm.extract_elements_as_pyobjects(iter.as_ref())
        ).into_pyobj(vm)
