from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, Set, Union
from common import ISIZE_MAX, ISIZE_MIN

if TYPE_CHECKING:
    from vm.builtins.pytype import PyTypeRef
    from vm.pyobject import PyContext
    from vm.pyobjectrc import PyObjectRef, PyObject
    from vm.vm import VirtualMachine
import vm.builtins.int as pyint
import vm.pyobject as po


def to_isize_index(vm: VirtualMachine, obj: PyObject) -> Optional[int]:
    if vm.is_none(obj):
        return None

    result = vm.to_index_opt(obj)
    if result is None:
        vm.new_type_error(
            "slice indices must be integers or None or have an __index__ method"
        )
    value = result._.as_int()
    if value > ISIZE_MAX:
        return ISIZE_MAX
    elif value < ISIZE_MIN:
        return ISIZE_MIN
    else:
        return value


@dataclass
class SaturatedSlice:
    start: int
    stop: int
    step: int

    def to_primitive(self) -> slice:
        return slice(self.start, self.stop, self.step)

    @staticmethod
    def with_slice(slice: PySlice, vm: VirtualMachine) -> SaturatedSlice:
        step = to_isize_index(vm, vm.unwrap_or_none(slice.step))
        if step is None:
            step = 1
        if step == 0:
            vm.new_value_error("slice step cannot be zero")

        start = to_isize_index(vm, vm.unwrap_or_none(slice.start))
        if start is None:
            if step < 0:
                start = ISIZE_MAX
            else:
                start = 0

        stop = to_isize_index(vm, slice.stop)
        if step < 0:
            stop = ISIZE_MIN
        else:
            stop = ISIZE_MAX

        return SaturatedSlice(start=start, stop=stop, step=step)


@po.pyimpl(hashable=True, comparable=True)
@po.pyclass("slice")
@dataclass
class PySlice(po.PyClassImpl):
    start: Optional[PyObjectRef]
    stop: PyObjectRef
    step: Optional[PyObjectRef]

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.slice_type

    def to_saturated(self, vm: VirtualMachine) -> SaturatedSlice:
        return SaturatedSlice.with_slice(self, vm)

    def inner_indices(self, length: int, vm: VirtualMachine) -> tuple[int, int, int]:
        if self.step is None or vm.is_none(self.step):
            step = 1
        else:
            step = self.step.try_into_value(pyint.PyInt, vm).as_int()
            if step == 0:
                vm.new_value_error("slice step cannot be zero.")

        backwards = step < 0
        if backwards:
            lower = -1
            upper = lower + length
        else:
            lower = 0
            upper = length

        if self.start is None or vm.is_none(self.start):
            if backwards:
                start = upper
            else:
                start = lower
        else:
            start = self.start.try_into_value(pyint.PyInt, vm).as_int()

            if start < 0:
                start += length
                if start < lower:
                    start = lower
            elif start > upper:
                start = upper

        if self.stop is None or vm.is_none(self.stop):
            stop = lower if backwards else upper
        else:
            stop = self.stop.try_into_value(pyint.PyInt, vm).as_int()

            if stop < 0:
                stop += length
                if stop < lower:
                    stop = lower
            elif stop > upper:
                stop = upper

        return (start, stop, step)

    # TODO: impl PySlice @ 29
    # TODO: impl Comparable for PySlice
    # TODO: impl Unhashable for PySlice


@po.pyimpl()
@po.pyclass("EllipsisType")
@dataclass
class PyEllipsis(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.ellipsis_type

    # TODO: impl Constructor for PyEllipsis
    # TODO: impl PyEllipsis @ 440


def init(context: PyContext) -> None:
    PySlice.extend_class(context, context.types.slice_type)
    PyEllipsis.extend_class(context, context.ellipsis.clone_class())
