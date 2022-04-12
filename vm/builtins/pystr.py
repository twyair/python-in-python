from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar, Optional, TypeAlias

if TYPE_CHECKING:
    from vm.function_ import FuncArgs
    from vm.builtins.bytes import PyBytesRef
    from vm.builtins.pytype import PyTypeRef
    from vm.pyobject import PyContext
    from vm.pyobjectrc import PyRef, PyObjectRef
    from vm.vm import VirtualMachine

import vm.pyobject as po
import vm.pyobjectrc as prc
import vm.types.slot as slot
import vm.builtins.iter as pyiter
import vm.protocol.mapping as mapping
import vm.protocol.sequence as sequence
import vm.function_ as vm_function_

from common.hash import PyHash
from common.deco import pymethod


@po.tp_flags(basetype=True)
@po.pyimpl(
    constructor=True,
    as_mapping=True,
    as_sequence=True,
    hashable=True,
    comparable=True,
    iterable=True,
)
@po.pyclass("str")
@dataclass
class PyStr(
    po.PyClassImpl,
    po.PyValueMixin,
    po.TryFromObjectMixin,
    slot.HashableMixin,
    slot.AsMappingMixin,
    slot.AsSequenceMixin,
    slot.ComparableMixin,
    slot.IterableMixin,
    slot.ConstructorMixin,
):
    value: str

    MAPPING_METHODS: ClassVar[mapping.PyMappingMethods] = mapping.PyMappingMethods(
        length=lambda m, vm: PyStr.mapping_downcast(m)._._len(),
        subscript=lambda m, needle, vm: PyStr.mapping_downcast(m)._._getitem(
            needle, vm
        ),
        ass_subscript=None,
    )

    SEQUENCE_METHODS: ClassVar[sequence.PySequenceMethods] = sequence.PySequenceMethods(
        length=lambda m, vm: PyStr.sequence_downcast(m)._._len(),
        concat=lambda m, other, vm: PyStr.i__add__(
            PyStr.sequence_downcast(m), other, vm
        ),
        repeat=lambda m, n, vm: PyStr._mul(PyStr.sequence_downcast(m), n, vm),
        item=None,  # TODO #lambda m, i, vm: PyStr.sequence_downcast(m)._.get_item_by_index(vm, i)
        contains=lambda m, needle, vm: PyStr.sequence_downcast(m)._._contains(
            needle, vm
        ),
        ass_item=None,
        inplace_concat=None,
        inplace_repeat=None,
    )

    @staticmethod
    def class_(vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.str_type

    @staticmethod
    def from_str(s: str, ctx: PyContext) -> PyStrRef:
        return PyStr.new_ref(PyStr(s), ctx)
        # return PyStr.new_ref(PyStr(
        #     bytes=s.encode(),
        #     kind=Utf8(0),  # FIXME
        #     hash=None
        # ), ctx)

    def as_str(self) -> str:
        return self.value

    @staticmethod
    def new_ref(s: PyStr, ctx: PyContext) -> PyStrRef:
        return prc.PyRef.new_ref(s, ctx.types.str_type, None)

    def _len(self) -> int:
        return len(self.value)

    @staticmethod
    def _mul(zelf: PyRef[PyStr], n: int, vm: VirtualMachine) -> PyStrRef:
        assert n >= 0, n
        return PyStr.new_ref(PyStr(zelf._.value * n), vm.ctx)

    def _contains(self, needle: PyObjectRef, vm: VirtualMachine) -> bool:
        raise NotImplementedError

    def _getitem(self, needle: PyObjectRef, vm: VirtualMachine) -> PyObjectRef:
        raise NotImplementedError

    @pymethod()
    @classmethod
    def i__add__(
        cls, zelf: PyObjectRef, other: PyObjectRef, vm: VirtualMachine
    ) -> PyObjectRef:
        value = other.downcast_ref(PyStr)
        if value is not None:
            return PyStr.new_ref(PyStr(zelf._.value + value._.value), vm.ctx)
        else:
            if (radd := vm.get_method(other, "__radd__")) is not None:
                return vm.invoke(radd, vm_function_.FuncArgs([zelf]))
            else:
                vm.new_type_error(
                    f'can only concatenate str (not "{other.class_()._.name()}") to str'
                )

    @classmethod
    def hash(cls, zelf: PyRef[PyStr], vm: VirtualMachine) -> PyHash:
        # FIXME?
        return hash(zelf._.as_str())

    @classmethod
    def cmp(
        cls,
        zelf: PyRef[PyStr],
        other: prc.PyObject,
        op: slot.PyComparisonOp,
        vm: VirtualMachine,
    ) -> po.PyComparisonValue:
        if (res := op.identical_optimization(zelf, other)) is not None:
            return po.PyComparisonValue(res)
        value = other.downcast_ref(PyStr)
        if value is None:
            return po.PyComparisonValue(None)
        return po.PyComparisonValue(op.eval_(zelf._.as_str(), value._.as_str()))

    @classmethod
    def iter(cls, zelf: PyRef[PyStr], vm: VirtualMachine) -> prc.PyObjectRef:
        return PyStrIterator((pyiter.PositionIterInternal.new(zelf, 0), 0)).into_object(
            vm
        )

    @classmethod
    def as_mapping(
        cls, zelf: PyRef[PyStr], vm: VirtualMachine
    ) -> mapping.PyMappingMethods:
        return cls.MAPPING_METHODS

    @classmethod
    def as_sequence(
        cls, zelf: PyRef[PyStr], vm: VirtualMachine
    ) -> sequence.PySequenceMethods:
        return cls.SEQUENCE_METHODS

    @classmethod
    def py_new(
        cls, class_: PyTypeRef, args: FuncArgs, vm: VirtualMachine
    ) -> prc.PyObjectRef:
        raise NotImplementedError

    # TODO: impl PyStr @ 323
    # TODO: impl PyStr @ 379


# TODO: delete
PyStrRef: TypeAlias = "PyRef[PyStr]"


@po.pyimpl(constructor=False, iter_next=True)
@po.pyclass("str_iterator")
@dataclass
class PyStrIterator(
    po.PyClassImpl,
    po.PyValueMixin,
    po.TryFromObjectMixin,
    slot.IterNextIterableMixin,
    slot.IterNextMixin,
):
    value: tuple[pyiter.PositionIterInternal[PyStrRef], int]

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.str_iterator_type

    @classmethod
    def next(cls, zelf: PyRef[PyStrIterator], vm: VirtualMachine) -> slot.PyIterReturn:
        raise NotImplementedError


def encode_string(
    s: PyStrRef,
    encoding: Optional[PyStrRef],
    errors: Optional[PyStrRef],
    vm: VirtualMachine,
) -> PyBytesRef:
    raise NotImplementedError


def init(ctx: PyContext) -> None:
    PyStr.extend_class(ctx, ctx.types.str_type)
    PyStrIterator.extend_class(ctx, ctx.types.str_iterator_type)
