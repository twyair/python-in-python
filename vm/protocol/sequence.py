from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Optional
if TYPE_CHECKING:
    from vm.pyobjectrc import PyObject, PyObjectRef
    from vm.vm import VirtualMachine


@dataclass
class PySequenceMethods:
    length: Optional[Callable[[PySequence, VirtualMachine], int]] = None
    concat: Optional[
        Callable[[PySequence, PyObject, VirtualMachine], PyObjectRef]
    ] = None
    repeat: Optional[Callable[[PySequence, int, VirtualMachine], PyObjectRef]] = None
    item: Optional[Callable[[PySequence, int, VirtualMachine], PyObjectRef]] = None
    ass_item: Optional[
        Callable[[PySequence, int, Optional[PyObjectRef], VirtualMachine], None]
    ] = None
    contains: Optional[Callable[[PySequence, PyObject, VirtualMachine], bool]] = None
    inplace_concat: Optional[
        Callable[[PySequence, PyObject, VirtualMachine], PyObjectRef]
    ] = None
    inplace_repeat: Optional[
        Callable[[PySequence, int, VirtualMachine], PyObjectRef]
    ] = None


@dataclass
class PySequence:
    obj: PyObject
    methods: Optional[PySequenceMethods]

    @staticmethod
    def from_pyobj(obj: PyObject) -> PySequence:
        return PySequence(obj, None)

    def methods_(self, vm: VirtualMachine) -> PySequenceMethods:
        cls = self.obj.class_()
        if not cls.is_(vm.ctx.types.dict_type):
            f = cls.payload.mro_find_map(lambda x: x.slots.as_sequence)
            if f is not None:
                self.methods = f(self.obj, vm)
                return self.methods
        self.methods = PySequenceMethods()
        return self.methods

    def length_opt(self, vm: VirtualMachine) -> Optional[int]:
        f = self.methods_(vm).length
        if f is None:
            return None
        return f(self, vm)

    def length(self, vm: VirtualMachine) -> int:
        r = self.length_opt(vm)
        if r is None:
            vm.new_type_error(
                f"'{self.obj.class_()}' is not a sequence or has no len()"
            )
        return r
