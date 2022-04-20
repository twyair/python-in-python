from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar, Optional, TypeAlias

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
import vm.builtins.tuple as pytuple
import vm.builtins.genericalias as pygenericalias
import vm.protocol.mapping as mapping
import vm.protocol.sequence as sequence
import vm.protocol.iter as viter
import vm.sliceable as sliceable

from common.deco import pyclassmethod, pymethod, pyslot
from common.error import unreachable, PyImplBase


@po.tp_flags(basetype=True)
@po.pyimpl(
    as_mapping=True,
    iterable=True,
    hashable=False,
    comparable=True,
    as_sequence=True,
)
@po.pyclass("list")
@dataclass
class PyList(
    po.PyClassImpl,
    slot.ComparableMixin,
    slot.IterableMixin,
    slot.AsMappingMixin,
    slot.AsSequenceMixin,
    sequence.MutObjectSequenceOpMixin,
):
    elements: list[PyObjectRef]

    MAPPING_METHODS: ClassVar[mapping.PyMappingMethods] = mapping.PyMappingMethods(
        length=lambda m, vm: PyList.mapping_downcast(m)._._len(),
        subscript=lambda m, needle, vm: PyList.mapping_downcast(m)._._getitem(
            needle, vm
        ),
        ass_subscript=lambda m, needle, value, vm: PyList.ass_subscript(
            PyList.mapping_downcast(m), needle, value, vm
        ),
    )

    # FIXME!!!
    SEQUENCE_METHODS: ClassVar[sequence.PySequenceMethods] = sequence.PySequenceMethods(
        length=lambda s, vm: PyList.sequence_downcast(s)._._len(),
        concat=lambda s, other, vm: PyList.sequence_downcast(s)._.concat(other, vm),
        repeat=lambda s, n, vm: PyList.sequence_downcast(s)._.i__mul__(n, vm=vm),
        item=lambda s, i, vm: PyList.sequence_downcast(s)._.get_item_by_index(vm, i),
        ass_item=lambda s, i, value, vm: PyList.ass_item(
            PyList.sequence_downcast(s), i, value, vm
        ),
        contains=lambda s, target, vm: PyList.sequence_downcast(s)._.mut_contains(
            vm, target
        ),
        inplace_concat=lambda s, other, vm: PyList.inplace_concat(
            PyList.sequence_downcast(s), other, vm
        ),
        inplace_repeat=lambda s, n, vm: PyList.i__imul__(
            PyList.sequence_downcast(s), n, vm=vm
        ),
    )

    @staticmethod
    def new_ref(value: list[PyObjectRef], ctx: PyContext) -> PyListRef:
        return prc.PyRef.new_ref(PyList(value), ctx.types.list_type, None)

    @staticmethod
    def class_(vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.list_type

    @classmethod
    def ass_item(
        cls,
        zelf: PyRef[PyList],
        i: int,
        value: Optional[PyObjectRef],
        vm: VirtualMachine,
    ) -> None:
        if value is not None:
            zelf._.set_item_by_index(vm, i, value)
        else:
            zelf._.del_item_by_index(vm, i)

    @classmethod
    def ass_subscript(
        cls,
        zelf: PyRef[PyList],
        needle: PyObjectRef,
        value: Optional[PyObjectRef],
        vm: VirtualMachine,
    ) -> None:
        if value is not None:
            zelf._._setitem(needle, value, vm)
        else:
            zelf._._delitem(needle, vm)

    @pymethod(True)
    def append(self, x: PyObjectRef, /, *, vm: VirtualMachine) -> None:
        self.elements.append(x)

    @pymethod(True)
    def extend(self, x: PyObjectRef, /, *, vm: VirtualMachine) -> None:
        new_elements = vm.extract_elements_as_pyobjects(x)
        self.elements.extend(new_elements)

    @pymethod(True)
    def insert(
        self, position: int, element: PyObjectRef, /, *, vm: VirtualMachine
    ) -> None:
        self.elements.insert(position, element)

    def concat(self, other: PyObject, vm: VirtualMachine) -> PyRef[PyList]:
        value = other.payload_if_subclass(PyList, vm)
        if value is None:
            vm.new_type_error(
                f"Cannot add {PyList.class_(vm)._.name()} and {other.class_()._.name()}"
            )
        return PyList.new_ref(self.elements + value.elements, vm.ctx)

    @pymethod(True)
    def i__add__(self, other: PyObjectRef, /, *, vm: VirtualMachine) -> PyRef[PyList]:
        return self.concat(other, vm)

    @staticmethod
    def inplace_concat(
        zelf: PyRef[PyList], other: PyObject, vm: VirtualMachine
    ) -> PyObjectRef:
        try:
            seq = sequence.PySequence.from_pyobj(other).extract_cloned(lambda x: x, vm)
        except PyImplBase as _:
            return vm.ctx.get_not_implemented()
        else:
            zelf._.elements.extend(seq)
            return zelf
        unreachable()

    @pymethod(True)
    @staticmethod
    def i__iadd__(
        zelf: PyRef[PyList], other: PyObjectRef, /, *, vm: VirtualMachine
    ) -> PyObjectRef:
        return PyList.inplace_concat(zelf, other, vm)

    @pymethod(True)
    def i__bool__(self, *, vm: VirtualMachine) -> bool:
        return bool(self.elements)

    @pymethod(True)
    def clear(self, *, vm: VirtualMachine) -> None:
        self.elements.clear()

    @pymethod(True)
    def copy(self, *, vm: VirtualMachine) -> PyRef[PyList]:
        return PyList.new_ref(self.elements.copy(), vm.ctx)

    def _len(self) -> int:
        return len(self.elements)

    @pymethod(True)
    def i__len__(self, *, vm: VirtualMachine) -> int:
        return self._len()

    @pymethod(True)
    def i__sizeof__(self, *, vm: VirtualMachine) -> int:
        return self.elements.__sizeof__()

    @pymethod(True)
    def reverse(self, *, vm: VirtualMachine) -> None:
        self.elements.reverse()

    @pymethod(True)
    @staticmethod
    def i__reversed__(
        zelf: PyObjectRef, *, vm: VirtualMachine
    ) -> PyRef[PyListReverseIterator]:
        position = zelf._._len() - 1
        return PyListReverseIterator(
            pyiter.PositionIterInternal.new(zelf, position)
        ).into_ref(vm)

    def index_in_range(self, i: int) -> bool:
        return not (i >= len(self.elements) or i < 0 and -i > len(self.elements))

    def del_item_by_index(self, vm: VirtualMachine, index: int) -> None:
        if not self.index_in_range(index):
            vm.new_index_error("assigment index out of range")
        del self.elements[index]

    def del_item_by_slice(
        self,
        vm: VirtualMachine,
        slice_: pyslice.SaturatedSlice,
    ) -> None:
        del self.elements[slice_.to_primitive()]

    def set_item_by_slice(
        self,
        vm: VirtualMachine,
        slice_: pyslice.SaturatedSlice,
        items: list[PyObjectRef],
    ) -> None:
        # TODO? vm.new_value_error("attempt to assign sequence of size {} to extended slice of size {}"?
        self.elements[slice_.to_primitive()] = items

    def set_item_by_index(
        self, vm: VirtualMachine, index: int, value: PyObjectRef
    ) -> None:
        if not self.index_in_range(index):
            vm.new_index_error("assigment index out of range")
        self.elements[index] = value

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
            return PyList.new_ref(self.get_item_by_slice(vm, i.value), vm.ctx)

    @pymethod(True)
    def i__getitem__(
        self, needle: PyObjectRef, /, *, vm: VirtualMachine
    ) -> PyObjectRef:
        return self._getitem(needle, vm)

    def _setitem(
        self, needle: PyObject, value: PyObjectRef, vm: VirtualMachine
    ) -> None:
        i = sliceable.SequenceIndex.try_from_borrowed_object(vm, needle)
        if isinstance(i, sliceable.SequenceIndexInt):
            self.set_item_by_index(vm, i.value, value)
        else:
            seq = sequence.PySequence.from_pyobj(value).extract_cloned(lambda x: x, vm)
            return self.set_item_by_slice(vm, i.value, seq)

    @pymethod(True)
    def i__setitem__(
        self, needle: PyObjectRef, value: PyObjectRef, /, *, vm: VirtualMachine
    ) -> None:
        self._setitem(needle, value, vm)

    @pymethod(True)
    @staticmethod
    def i__repr__(zelf: PyRef[PyList], *, vm: VirtualMachine) -> str:
        raise NotImplementedError

    @pymethod(True)
    def i__mul__(self, n: int, /, *, vm: VirtualMachine) -> PyRef[PyList]:
        return PyList.new_ref(self.elements * n, vm.ctx)

    @pymethod(True)
    def i__rmul__(self, n: int, /, *, vm: VirtualMachine) -> PyRef[PyList]:
        return self.i__mul__(n, vm=vm)

    @pymethod(True)
    @staticmethod
    def i__imul__(
        zelf: PyRef[PyList], n: int, /, *, vm: VirtualMachine
    ) -> PyRef[PyList]:
        zelf._.elements *= n
        return zelf

    @pymethod(True)
    def count(self, needle: PyObjectRef, /, *, vm: VirtualMachine) -> int:
        return self.mut_count(vm, needle)

    @pymethod(True)
    def i__contains__(self, needle: PyObjectRef, /, *, vm: VirtualMachine) -> bool:
        return self.mut_contains(vm, needle)

    @pymethod(True)
    def index(
        self,
        needle: PyObjectRef,
        start: Optional[int] = None,
        stop: Optional[int] = None,
        *,
        vm: VirtualMachine,
    ) -> int:
        raise NotImplementedError

    @pymethod(True)
    def pop(self, i: Optional[int], /, *, vm: VirtualMachine) -> PyObjectRef:
        if i is None:
            i = -1
        if i < 0:
            i += len(self.elements)
        if not self.elements:
            vm.new_index_error("pop from empty list")
        elif i < 0 or i >= len(self.elements):
            vm.new_index_error("pop index out of range")
        else:
            return self.elements.pop(i)

    @pymethod(True)
    def remove(self, needle: PyObjectRef, /, *, vm: VirtualMachine) -> None:
        index = self.mut_index(vm, needle)
        if index is not None:
            return
        else:
            vm.new_value_error(f"'{needle.str(vm)}' is not in list")

    def _delitem(self, needle: PyObject, vm: VirtualMachine) -> None:
        i = sliceable.SequenceIndex.try_from_borrowed_object(vm, needle)
        if isinstance(i, sliceable.SequenceIndexInt):
            self.del_item_by_index(vm, i.value)
        else:
            self.del_item_by_slice(vm, i.value)

    @pymethod(True)
    def i__delitem__(self, subscript: PyObjectRef, /, *, vm: VirtualMachine) -> None:
        self._delitem(subscript, vm)

    @pymethod(False)
    def sort(self, args: FuncArgs, *, vm: VirtualMachine) -> None:
        raise NotImplementedError

    @pyslot
    @staticmethod
    def slot_new(
        class_: PyTypeRef, fargs: FuncArgs, *, vm: VirtualMachine
    ) -> PyObjectRef:
        return PyList.default().into_pyresult_with_type(vm, class_)

    @pymethod(True)
    def i__init__(
        self, iterable: Optional[PyObjectRef] = None, *, vm: VirtualMachine
    ) -> None:
        if iterable is not None:
            self.elements = vm.extract_elements_as_pyobjects(iterable)
        else:
            self.elements = []

    @pyclassmethod(False)
    @staticmethod
    def i__class_getitem__(
        class_: PyTypeRef, args: PyObjectRef, /, *, vm: VirtualMachine
    ) -> pygenericalias.PyGenericAlias:
        return pygenericalias.PyGenericAlias.new(class_, args, vm)

    @staticmethod
    def default() -> PyList:
        return PyList([])

    @classmethod
    def cmp(
        cls,
        zelf: PyRef[PyList],
        other: PyObject,
        op: slot.PyComparisonOp,
        vm: VirtualMachine,
    ) -> po.PyComparisonValue:
        if (res := op.identical_optimization(zelf, other)) is not None:
            return po.PyComparisonValue(res)
        # class_or_notimplemented! is a macro
        value = other.downcast_ref(PyList)
        if value is None:
            return po.PyComparisonValue(None)
        return po.PyComparisonValue(op.eval_(zelf._.elements, value._.elements))

    @classmethod
    def iter(cls, zelf: PyRef[PyList], vm: VirtualMachine) -> PyObjectRef:
        return PyListIterator(pyiter.PositionIterInternal.new(zelf, 0)).into_ref(vm)

    @classmethod
    def as_mapping(
        cls, zelf: PyRef[PyList], vm: VirtualMachine
    ) -> mapping.PyMappingMethods:
        return cls.MAPPING_METHODS

    @classmethod
    def as_sequence(
        cls, zelf: PyRef[PyList], vm: VirtualMachine
    ) -> sequence.PySequenceMethods:
        return cls.SEQUENCE_METHODS

    @classmethod
    def do_get(cls, index: int, guard: list[PyObjectRef]) -> Optional[PyObjectRef]:
        return guard[index]

    def do_lock(self) -> list[PyObjectRef]:
        return self.elements


PyListRef: TypeAlias = "PyRef[PyList]"


@po.pyimpl(constructor=False, iter_next=True)
@po.pyclass("list_iterator")
@dataclass
class PyListIterator(po.PyClassImpl, slot.IterNextIterableMixin, slot.IterNextMixin):
    internal: pyiter.PositionIterInternal[PyListRef]

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.list_iterator_type

    @pymethod(True)
    def i__length_hint__(self, *, vm: VirtualMachine) -> int:
        return self.internal.length_hint(lambda obj: obj._._len())

    @pymethod(True)
    def i__setstate__(self, state: PyObjectRef, *, vm: VirtualMachine) -> None:
        self.internal.set_state(state, lambda obj, pos: min(pos, obj._._len()), vm)

    @pymethod(True)
    def i__reduce__(self, *, vm: VirtualMachine) -> pytuple.PyTupleRef:
        return self.internal.builtins_iter_reduce(lambda x: x, vm)

    @classmethod
    def next(
        cls, zelf: PyRef[PyListIterator], vm: VirtualMachine
    ) -> viter.PyIterReturn:
        return zelf._.internal.next(
            lambda l, pos: viter.PyIterReturn.from_pyresult(
                lambda: l._.get_item_by_index(vm, pos), vm
            )
        )


@po.pyimpl(constructor=False, iter_next=True)
@po.pyclass("list_reverse_iterator")
@dataclass
class PyListReverseIterator(
    po.PyClassImpl, slot.IterNextMixin, slot.IterNextIterableMixin
):
    internal: pyiter.PositionIterInternal[PyListRef]

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.list_reverseiterator_type

    @pymethod(True)
    def i__length_hint__(self, *, vm: VirtualMachine) -> int:
        return self.internal.length_hint(lambda obj: obj._._len())

    @pymethod(True)
    def i__setstate__(self, state: PyObjectRef, *, vm: VirtualMachine) -> None:
        self.internal.set_state(state, lambda obj, pos: min(pos, obj._._len()), vm)

    @pymethod(True)
    def i__reduce__(self, *, vm: VirtualMachine) -> pytuple.PyTupleRef:
        return self.internal.builtins_reversed_reduce(lambda x: x, vm)

    @classmethod
    def next(
        cls, zelf: PyRef[PyListIterator], vm: VirtualMachine
    ) -> viter.PyIterReturn:
        return zelf._.internal.rev_next(
            lambda l, pos: viter.PyIterReturn.from_pyresult(
                lambda: l._.get_item_by_index(vm, pos), vm
            )
        )


def init(context: PyContext) -> None:
    PyList.extend_class(context, context.types.list_type)
    PyListIterator.extend_class(context, context.types.list_iterator_type)
    PyListReverseIterator.extend_class(context, context.types.list_reverseiterator_type)
