from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Optional, TypeAlias, TypeVar

if TYPE_CHECKING:
    from vm.pyobjectrc import PyObject, PyObjectRef
    from vm.vm import VirtualMachine
from common import ISIZE_MAX


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


R = TypeVar("R")


@dataclass
class PySequence:
    obj: PyObject
    methods: Optional[PySequenceMethods]

    @staticmethod
    def from_pyobj(obj: PyObject) -> PySequence:
        # FIXME?
        return PySequence(obj, None)

    def check(self, vm: VirtualMachine) -> bool:
        return self.methods_(vm).item is not None

    @staticmethod
    def with_methods(obj: PyObjectRef, methods: PySequenceMethods) -> PySequence:
        return PySequence(obj, methods)

    @staticmethod
    def try_protocol(obj: PyObject, vm: VirtualMachine) -> PySequence:
        zelf = PySequence.from_pyobj(obj)
        if zelf.check(vm):
            return zelf
        else:
            vm.new_type_error(f"'{obj.class_()._.name()}' is not a sequence")

    def methods_(self, vm: VirtualMachine) -> PySequenceMethods:
        cls = self.obj.class_()
        if not cls.is_(vm.ctx.types.dict_type):
            f = cls._.mro_find_map(lambda x: x.slots.as_sequence)
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

    def contains(self, key: PyObjectRef, vm: VirtualMachine) -> bool:
        f = self.methods_(vm).contains
        if f is None:
            raise NotImplementedError
        return f(self, key, vm)

    # TODO: impl: repeat, item, ass_item, concat, inplace_concat, inplace_repeat

    def get_item(self, pos: int, vm: VirtualMachine) -> PyObjectRef:
        if (f := self.methods_(vm).item) is not None:
            return f(self, pos, vm)
        vm.new_type_error(
            "'{}' is not a sequence or does not support indexing".format(
                self.obj.class_()
            )
        )

    def extract_cloned(
        self, f: Callable[[PyObjectRef], R], vm: VirtualMachine
    ) -> list[R]:
        import vm.builtins.tuple as pytuple
        import vm.builtins.list as pylist

        if (t := self.obj.payload_if_exact(pytuple.PyTuple, vm)) is not None:
            return [f(x) for x in t.as_slice()]
        elif (t := self.obj.payload_if_exact(pylist.PyList, vm)) is not None:
            return [f(x) for x in t.elements]
        else:
            # TODO: impl `__iter__` for `PyIterIter`
            return [f(x) for x in self.obj.get_iter(vm).iter(vm)]
