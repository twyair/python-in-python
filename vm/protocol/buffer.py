from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from vm.pyobjectrc import PyObjectRef
    from vm.vm import VirtualMachine


@dataclass
class BufferMethods:
    obj_bytes: Callable[[PyBuffer], bytes]
    obj_bytes_mut: Callable[[PyBuffer], bytearray]
    release: Callable[[PyBuffer], None]
    retain: Callable[[PyBuffer], None]


@dataclass
class PyBuffer:
    obj: PyObjectRef
    desc: BufferDescriptor
    methods: BufferMethods

    @staticmethod
    def try_from_borrowed_object(vm: VirtualMachine, obj: PyObjectRef) -> PyBuffer:
        cls = obj.class_()
        if (f := cls.payload.mro_find_map(lambda c: c.slots.as_buffer)) is not None:
            return f(obj, vm)
        vm.new_type_error(
            f"a bytes-like object is required, not '{cls.payload.name()}'"
        )


@dataclass
class BufferDescriptor:
    len: int
    readonly: bool
    itemsize: int
    format: str
    dim_desc: list[tuple[int, int, int]]

    def is_contiguous(self) -> bool:
        if self.len == 0:
            return True
        sd = self.itemsize
        for (shape, stride, _) in self.dim_desc:
            if shape > 1 and stride != sd:
                return False
            sd *= shape
        return True