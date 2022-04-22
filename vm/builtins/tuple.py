from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar, Generic, Optional, Type, TypeAlias, TypeVar
from common.deco import pyclassmethod, pymethod
from common.error import PyImplBase, PyImplError
from common.hash import PyHash, hash_iter

if TYPE_CHECKING:
    from vm.builtins.pytype import PyTypeRef
    from vm.pyobject import PyContext
    from vm.pyobjectrc import PyObjectRef, PyRef, PyObject
    from vm.vm import VirtualMachine
    from vm.function_ import FuncArgs

import vm.pyobject as po
import vm.pyobjectrc as prc
import vm.types.slot as slot
import vm.builtins.iter as pyiter
import vm.builtins.slice as pyslice
import vm.builtins.genericalias as pygenericalias
import vm.utils as utils
import vm.sliceable as sliceable
import vm.protocol.mapping as mapping
import vm.protocol.sequence as sequence
import vm.protocol.iter as protocol_iter
from common import ISIZE_MAX


@po.tp_flags(basetype=True)
@po.pyimpl(
    as_mapping=True,
    as_sequence=True,
    hashable=True,
    comparable=True,
    iterable=True,
    constructor=True,
)
@po.pyclass("tuple")
@dataclass
class PyTuple(
    po.PyClassImpl,
    slot.ComparableMixin,
    slot.IterableMixin,
    slot.ConstructorMixin,
    slot.HashableMixin,
    slot.AsMappingMixin,
    slot.AsSequenceMixin,
):
    elements: list[PyObjectRef]

    MAPPING_METHODS: ClassVar[mapping.PyMappingMethods] = mapping.PyMappingMethods(
        length=lambda m, vm: PyTuple.mapping_downcast(m)._.len(),
        subscript=lambda m, needle, vm: PyTuple.mapping_downcast(m)._._getitem(
            needle, vm
        ),
        ass_subscript=None,
    )

    SEQUENCE_METHODS: ClassVar[sequence.PySequenceMethods] = sequence.PySequenceMethods(
        length=lambda s, vm: PyTuple.sequence_downcast(s)._.len(),
        concat=None,  # TODO
        repeat=lambda s, n, vm: PyTuple.i__mul__(
            PyTuple.sequence_downcast(s), n, vm=vm
        ),
        item=lambda s, i, vm: PyTuple.sequence_downcast(s)._.get_item_by_index(vm, i),
        contains=lambda s, needle, vm: PyTuple.sequence_downcast(s)._._contains(
            needle, vm
        ),
        ass_item=None,
        inplace_concat=None,
        inplace_repeat=None,
    )

    def as_slice(self) -> list[PyObjectRef]:
        return self.elements

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.tuple_type

    @staticmethod
    def new_ref(elements: list[PyObjectRef], ctx: PyContext) -> PyTupleRef:
        if not elements:
            return ctx.empty_tuple
        else:
            return prc.PyRef.new_ref(PyTuple(elements), ctx.types.tuple_type, None)

    def intro_ref(self: PyTuple, vm: VirtualMachine) -> PyTupleRef:
        return prc.PyRef.new_ref(self, vm.ctx.types.tuple_type, None)

    def len(self) -> int:
        return len(self.elements)

    def __len__(self) -> int:
        return self.len()

    def fast_getitem(self, i: int) -> PyObjectRef:
        return self.elements[i]

    @pymethod(True)
    @staticmethod
    def i__add__(
        zelf: PyRef[PyTuple], other: PyObjectRef, /, *, vm: VirtualMachine
    ) -> po.PyArithmeticValue[PyRef[PyTuple]]:
        try:
            value = other.downcast(PyTuple)
        except PyImplBase as _:
            return po.PyArithmeticValue(None)
        else:
            return po.PyArithmeticValue(
                PyTuple(zelf._.elements + value._.elements).into_ref(vm)
            )

    @pymethod(True)
    def i__bool__(self, *, vm: VirtualMachine) -> bool:
        return bool(self.elements)

    @pymethod(True)
    def count(self, needle: PyObjectRef, /, *, vm: VirtualMachine) -> int:
        return sum(
            1 if vm.identical_or_equal(element, needle) else 0  # for readability's sake
            for element in self.elements
        )

    @pymethod(True)
    def i__len__(self, *, vm: VirtualMachine) -> int:
        return len(self.elements)

    def is_empty(self) -> bool:
        return not self.elements

    @pymethod(True)
    @staticmethod
    def i__repr__(zelf: PyRef[PyTuple], *, vm: VirtualMachine) -> str:
        raise NotImplementedError

    @pymethod(True)
    @staticmethod
    def i__mul__(
        zelf: PyRef[PyTuple], value: int, /, *, vm: VirtualMachine
    ) -> PyRef[PyTuple]:
        if zelf._.is_empty() or value == 0:
            return vm.ctx.empty_tuple
        elif value == 1 and zelf.class_().is_(vm.ctx.types.tuple_type):
            return zelf
        else:
            return PyTuple(zelf._.elements * value).into_ref(vm)

    @pymethod(True)
    @staticmethod
    def i__rmul__(
        zelf: PyRef[PyTuple], value: int, /, *, vm: VirtualMachine
    ) -> PyRef[PyTuple]:
        return PyTuple.i__mul__(zelf, value, vm=vm)

    def index_in_range(self, i: int) -> bool:
        return not (i >= len(self.elements) or i < 0 and -i > len(self.elements))

    def get_item_by_index_opt(
        self, vm: VirtualMachine, i: int
    ) -> Optional[PyObjectRef]:
        if not self.index_in_range(i):
            return None
        return self.elements[i]

    def get_item_by_index(self, vm: VirtualMachine, i: int) -> PyObjectRef:
        if not self.index_in_range(i):
            vm.new_index_error("index out of range")
        return self.elements[i]

    def get_item_by_slice(
        self, vm: VirtualMachine, s: pyslice.SaturatedSlice
    ) -> list[PyObjectRef]:
        return self.elements[s.to_primitive()]

    def _getitem(self, needle: PyObject, vm: VirtualMachine) -> PyObjectRef:
        i = sliceable.SequenceIndex.try_from_borrowed_object(vm, needle)
        if isinstance(i, sliceable.SequenceIndexInt):
            return self.get_item_by_index(vm, i.value)
        else:
            return PyTuple(self.get_item_by_slice(vm, i.value)).into_ref(vm)

    @pymethod(True)
    def i__getitem__(
        self, needle: PyObjectRef, /, *, vm: VirtualMachine
    ) -> PyObjectRef:
        return self._getitem(needle, vm)

    @pymethod(True)
    def index(
        self,
        needle: PyObjectRef,
        start: Optional[int] = None,
        stop: Optional[int] = None,
        /,
        *,
        vm: VirtualMachine,
    ) -> int:
        if start is None:
            start = 0
        if start < 0:
            start += self.len()
            if start < 0:
                start = 0
        if stop is None:
            stop = ISIZE_MAX
        if stop < 0:
            stop += self.len()
            if stop < 0:
                stop = 0
        for index, element in enumerate(self.elements[start:stop], start):
            if vm.identical_or_equal(element, needle):
                return index
        vm.new_value_error("tuple.index(x): x not in tuple")

    def _contains(self, needle: PyObjectRef, vm: VirtualMachine) -> bool:
        return any(vm.identical_or_equal(element, needle) for element in self.elements)

    @pymethod(True)
    def i__contains__(self, needle: PyObjectRef, /, *, vm: VirtualMachine) -> bool:
        return self._contains(needle, vm)

    @pymethod(True)
    @staticmethod
    def i__getnewargs__(zelf: PyRef[PyTuple], *, vm: VirtualMachine) -> PyTupleRef:
        if zelf.class_().is_(vm.ctx.types.tuple_type):
            tuple_arg = zelf
        else:
            tuple_arg = PyTuple.new_ref(zelf._.elements.copy(), vm.ctx)
        return PyTuple([tuple_arg]).into_ref(vm)

    @pyclassmethod(True)
    @staticmethod
    def class_getitem(
        cls_: PyTypeRef, args: PyObjectRef, vm: VirtualMachine
    ) -> pygenericalias.PyGenericAlias:
        return pygenericalias.PyGenericAlias.new(cls_, args, vm)

    @classmethod
    def hash(cls, zelf: PyRef[PyTuple], vm: VirtualMachine) -> PyHash:
        return hash_iter(iter(zelf._.elements), vm)

    @classmethod
    def py_new(
        cls, class_: PyTypeRef, fargs: FuncArgs, /, vm: VirtualMachine
    ) -> PyObjectRef:
        iterable: PyObjectRef = fargs.bind(__py_new_args).args[0]
        if iterable is not None:
            if class_.is_(vm.ctx.types.tuple_type):
                try:
                    return iterable.downcast_exact(PyTuple, vm)
                except PyImplError as e:
                    iterable = e.obj
            elements = vm.extract_elements_as_pyobjects(iterable)
        else:
            elements = []

        if not elements and class_.is_(vm.ctx.types.tuple_type):
            return vm.ctx.empty_tuple
        else:
            return PyTuple(elements).into_pyresult_with_type(vm, class_)

    @classmethod
    def cmp(
        cls,
        zelf: PyRef[PyTuple],
        other: PyObject,
        op: slot.PyComparisonOp,
        vm: VirtualMachine,
    ) -> po.PyComparisonValue:
        if (res := op.identical_optimization(zelf, other)) is not None:
            return po.PyComparisonValue(res)
        else:
            value = other.downcast_ref(PyTuple)
            if value is None:
                return po.PyComparisonValue(None)
            return po.PyComparisonValue(op.eval_(zelf._.elements, value._.elements))

    @classmethod
    def iter(cls, zelf: PyRef[PyTuple], vm: VirtualMachine) -> PyObjectRef:
        return PyTupleIterator(pyiter.PositionIterInternal.new(zelf, 0)).into_ref(vm)

    @classmethod
    def as_mapping(
        cls, zelf: PyRef[PyTuple], vm: VirtualMachine
    ) -> mapping.PyMappingMethods:
        return cls.MAPPING_METHODS

    @classmethod
    def as_sequence(
        cls, zelf: PyRef[PyTuple], vm: VirtualMachine
    ) -> sequence.PySequenceMethods:
        return cls.SEQUENCE_METHODS


PyTupleRef: TypeAlias = "PyRef[PyTuple]"


def __py_new_args(x: Optional[PyObjectRef] = None, /):
    ...


@po.pyimpl(constructor=False, iter_next=True)
@po.pyclass("tuple_iterator")
@dataclass
class PyTupleIterator(
    po.PyClassImpl,
    slot.IterNextMixin,
    slot.IterNextIterableMixin,
):
    internal: pyiter.PositionIterInternal[PyTupleRef]

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.tuple_iterator_type

    @pymethod(True)
    def i__length_hint__(self, *, vm: VirtualMachine) -> int:
        return self.internal.length_hint(lambda x: x._.len())

    @pymethod(True)
    def i__setstate__(self, state: PyObjectRef, *, vm: VirtualMachine) -> None:
        self.internal.set_state(state, lambda obj, pos: min(pos, obj._.len()), vm)

    @pymethod(True)
    def i__reduce__(self, *, vm: VirtualMachine) -> PyTupleRef:
        raise NotImplementedError

    @classmethod
    def next(
        cls, zelf: PyRef[PyTupleIterator], vm: VirtualMachine
    ) -> protocol_iter.PyIterReturn:
        return zelf._.internal.next(
            lambda tup, pos: protocol_iter.PyIterReturn.from_option(
                tup._.get_item_by_index_opt(vm, pos)
            )
        )


T = TypeVar("T")


@dataclass
class PyTupleTyped(Generic[T]):
    tuple: PyTupleRef

    @staticmethod
    def try_from_object(
        t: Type[T], vm: VirtualMachine, obj: PyObjectRef
    ) -> PyTupleTyped[PyRef[T]]:
        tup = PyTuple.try_from_object(vm, obj)
        for elem in tup._.as_slice():
            vm.check(t, elem)  # type: ignore
        return PyTupleTyped(tup)

    def __len__(self) -> int:
        return len(self.tuple._.elements)

    def is_empty(self) -> bool:
        return self.tuple._.is_empty()

    def as_slice(self) -> list[T]:
        return self.tuple._.elements  # type: ignore

    def into_pyobject(self, vm: VirtualMachine) -> PyObjectRef:
        return self.tuple


def init(context: PyContext) -> None:
    PyTuple.extend_class(context, context.types.tuple_type)
    PyTupleIterator.extend_class(context, context.types.tuple_iterator_type)
