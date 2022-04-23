from __future__ import annotations
from abc import ABC, abstractmethod

from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar, Iterator, Optional, Type, TypeAlias, TypeVar

if TYPE_CHECKING:
    from vm.builtins.pytype import PyTypeRef
    from vm.pyobject import PyContext
    from vm.pyobjectrc import PyObjectRef, PyRef
    from vm.vm import VirtualMachine

import vm.function.arguments as arguments
import vm.builtins.genericalias as pygenericalias
import vm.builtins.set as pyset
import vm.function_ as vm_function_
import vm.protocol.mapping as mapping
import vm.protocol.sequence as sequence
import vm.builtins.iter as pyiter
import vm.pyobject as po
import vm.pyobjectrc as prc
import vm.types.slot as slot
from vm.dictdatatype import Dict as DictContentType

from common.deco import pyclassmethod, pymethod, pyslot


@po.tp_flags(basetype=True)
@po.pyimpl(
    as_mapping=True, hashable=False, comparable=True, iterable=True, as_sequence=True
)
@po.pyclass("dict")
@dataclass
class PyDict(
    po.PyClassImpl,
    slot.AsMappingMixin,
    slot.AsSequenceMixin,
    slot.IterableMixin,
    slot.ComparableMixin,
):
    entries: DictContentType

    MAPPING_METHODS: ClassVar = mapping.PyMappingMethods(
        length=lambda m, vm: PyDict.mapping_downcast(m)._.len(),
        subscript=lambda m, k, vm: PyDict.mapping_downcast(m)._.get_item(k, vm),
        ass_subscript=lambda m, k, v, vm: PyDict.ass_subscript(m, k, v, vm),
    )

    SEQUENCE_METHODS: ClassVar = sequence.PySequenceMethods(
        contains=lambda s, target, vm: PyDict.sequence_downcast(s)._.entries.contains(
            vm, target
        )
    )

    @staticmethod
    def new_ref(ctx: PyContext) -> PyDictRef:
        return prc.PyRef.new_ref(PyDict(DictContentType()), ctx.types.dict_type, None)

    @staticmethod
    def class_(vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.dict_type

    @classmethod
    def ass_subscript(
        cls,
        m: mapping.PyMapping,
        key: PyObjectRef,
        value: Optional[PyObjectRef],
        vm: VirtualMachine,
    ) -> None:
        zelf = cls.mapping_downcast(m)
        if value is not None:
            zelf._.inner_setitem(key, value, vm)
        else:
            zelf._.del_item(key, vm)

    @staticmethod
    def from_attributes(attrs: po.PyAttributes, vm: VirtualMachine) -> PyDict:
        d = DictContentType()
        for key, value in attrs.items():
            d.insert(vm, vm.ctx.new_str(key), value)
        return PyDict(d)

    def get_keys(self) -> Iterator[PyObjectRef]:
        return iter(self.entries.keys())

    def missing_opt(
        self, key: PyObjectRef, vm: VirtualMachine
    ) -> Optional[PyObjectRef]:
        method = vm.get_method(self.into_ref(vm), "__missing__")
        if method is None:
            return None
        return vm.invoke(method, vm_function_.FuncArgs([key]))

    def inner_getitem_opt(
        self, key: PyObjectRef, vm: VirtualMachine
    ) -> Optional[PyObjectRef]:
        if (value := self.entries.get(vm, key)) is not None:
            return value
        elif (value := self.missing_opt(key, vm)) is not None:
            return value
        return None

    def inner_getitem(self, key: PyObjectRef, vm: VirtualMachine) -> PyObjectRef:
        value = self.inner_getitem_opt(key, vm)
        if value is None:
            vm.new_key_error(key)
        return value

    def inner_setitem(
        self, key: PyObjectRef, value: PyObjectRef, vm: VirtualMachine
    ) -> None:
        self.entries.insert(vm, key, value)

    def inner_delitem(self, key: PyObjectRef, vm: VirtualMachine) -> None:
        self.entries.delete(vm, key)

    def get_item_opt(
        self, key: PyObjectRef, vm: VirtualMachine
    ) -> Optional[PyObjectRef]:
        # FIXME? impl for PyObjectView<PyDict>
        return self.inner_getitem_opt(key, vm)

    def get_item(self, key: PyObjectRef, vm: VirtualMachine) -> PyObjectRef:
        # FIXME? impl for PyObjectView<PyDict>
        return self.inner_getitem(key, vm)

    def contains_key(self, key: PyObjectRef, vm: VirtualMachine) -> bool:
        return self.entries.contains(vm, key)

    def set_item(
        self, key: PyObjectRef, value: PyObjectRef, vm: VirtualMachine
    ) -> None:
        # FIXME? impl for PyObjectView<PyDict>
        self.inner_setitem(key, value, vm)

    def del_item(self, key: PyObjectRef, vm: VirtualMachine) -> None:
        # FIXME? impl for PyObjectView<PyDict>
        self.inner_delitem(key, vm)

    def get_chain(
        self, other: PyDict, key: PyObjectRef, vm: VirtualMachine
    ) -> Optional[PyObjectRef]:
        # FIXME? impl for PyObjectView<PyDict>
        return self.entries.get_chain(vm, other.entries, key)

    @staticmethod
    def default() -> PyDict:
        return PyDict(DictContentType())

    @pyslot
    @staticmethod
    def slot_new(
        class_: PyTypeRef, fargs: vm_function_.FuncArgs, vm: VirtualMachine
    ) -> PyObjectRef:
        # NOTE: `fargs` is ignored: `dict.__new__(dict, 1, 2, 3, k=4)` ==> `{}`
        return PyDict.default().into_pyresult_with_type(vm, class_)

    @pymethod(True)
    def i__sizeof__(self, *, vm: VirtualMachine) -> int:
        return self.entries.__sizeof__()

    @pymethod(True)
    def i__repr__(self, *, vm: VirtualMachine) -> str:
        raise NotImplementedError

    def len(self) -> int:
        return self.entries.len()

    @pymethod(True)
    def i__len__(self, *, vm: VirtualMachine) -> int:
        return self.len()

    @pymethod(True)
    def i__bool__(self, *, vm: VirtualMachine) -> bool:
        return bool(self.entries)

    @pymethod(True)
    @staticmethod
    def items(zelf: PyRef[PyDict], *, vm: VirtualMachine) -> PyObjectRef:
        return PyDictItems.new(zelf).into_ref(vm)

    @pymethod(True)
    def i__setitem__(
        self, key: PyObjectRef, value: PyObjectRef, *, vm: VirtualMachine
    ) -> None:
        self.inner_setitem(key, value, vm)

    @pymethod(True)
    def i__getitem__(self, key: PyObjectRef, vm: VirtualMachine) -> PyObjectRef:
        return self.inner_getitem(key, vm)

    @pymethod(True)
    def i__contains__(self, key: PyObjectRef, /, *, vm: VirtualMachine) -> bool:
        return self.entries.contains(vm, key)

    @pymethod(True)
    def get(
        self, key: PyObjectRef, default: Optional[PyObjectRef], vm: VirtualMachine
    ) -> PyObjectRef:
        value = self.entries.get(vm, key)
        if value is None:
            return vm.unwrap_or_none(default)
        return value

    @pymethod(True)
    def setdefault(
        self, key: PyObjectRef, default: Optional[PyObjectRef], vm: VirtualMachine
    ) -> PyObjectRef:
        return self.entries.setdefault(vm, key, lambda: vm.unwrap_or_none(default))

    @pymethod(True)
    def copy(self, *, vm: VirtualMachine) -> PyDict:
        return PyDict(self.entries.clone())

    @pymethod(True)
    def i__delitem__(self, key: PyObjectRef, /, *, vm: VirtualMachine) -> None:
        self.inner_delitem(key, vm)

    @pymethod(True)
    def clear(self, *, vm: VirtualMachine) -> None:
        self.entries.clear()

    @pymethod(True)
    @staticmethod
    def keys(zelf: PyRef[PyDict], *, vm: VirtualMachine) -> PyDictKeys:
        return PyDictKeys.new(zelf)

    @pymethod(True)
    @staticmethod
    def values(zelf: PyRef[PyDict], *, vm: VirtualMachine) -> PyDictValues:
        return PyDictValues.new(zelf)

    @pymethod(True)
    def i__init__(
        self,
        dict_obj: Optional[PyObjectRef] = None,
        *,
        vm: VirtualMachine,
        **kwargs: PyObjectRef,
    ) -> None:
        self.update(dict_obj, **kwargs, vm=vm)

    @pyclassmethod(True)
    @staticmethod
    def fromkeys(
        class_: PyTypeRef,
        iterable: arguments.ArgIterable,
        value: Optional[PyObjectRef],
        *,
        vm: VirtualMachine,
    ) -> PyObjectRef:
        raise NotImplementedError

    @staticmethod
    def merge_object(
        dict: DictContentType, other: PyObjectRef, vm: VirtualMachine
    ) -> None:
        if (value := other.downcast_ref_if_exact(PyDict, vm)) is not None:
            return PyDict.merge_dict(dict, value, vm)
        raise NotImplementedError

    @staticmethod
    def merge_dict(
        dict: DictContentType, dict_other: PyDictRef, vm: VirtualMachine
    ) -> None:
        for key, value in dict_other._.entries.items():
            dict.insert(vm, key, value)
        # TODO: if dict_other.entries.has_changed_size(dict_size) {
        # return Err(vm.new_runtime_error("dict mutated during update".to_owned()));

    @pymethod(True)
    def update(
        self,
        dict_obj: Optional[PyObjectRef] = None,
        *,
        vm: VirtualMachine,
        **kwargs: PyObjectRef,
    ) -> None:
        if dict_obj is not None:
            return PyDict.merge_object(self.entries, dict_obj, vm)
        for key, value in kwargs.items():
            self.entries.insert(vm, vm.ctx.new_str(key), value)

    @pymethod(True)
    @staticmethod
    def i__ior__(
        zelf: PyRef[PyDict], other: PyObjectRef, *, vm: VirtualMachine
    ) -> PyDictRef:
        PyDict.merge_object(zelf._.entries, other, vm)
        return zelf

    @pymethod(True)
    @staticmethod
    def i__ror__(
        zelf: PyRef[PyDict], other: PyObjectRef, *, vm: VirtualMachine
    ) -> PyObjectRef:
        raise NotImplementedError

    @pymethod(True)
    def i__or__(self, other: PyObjectRef, *, vm: VirtualMachine) -> PyObjectRef:
        raise NotImplementedError

    @pymethod(True)
    def pop(
        self,
        key: PyObjectRef,
        default: Optional[PyObjectRef] = None,
        /,
        *,
        vm: VirtualMachine,
    ) -> PyObjectRef:
        if (value := self.entries.pop(vm, key)) is not None:
            return value
        elif default is not None:
            return default
        else:
            vm.new_key_error(key)

    @pymethod(True)
    def popitem(self, *, vm: VirtualMachine) -> PyObjectRef:
        raise NotImplementedError

    @pymethod(True)
    @staticmethod
    def reversed(
        zelf: PyRef[PyDict], *, vm: VirtualMachine
    ) -> PyDictReverseKeyIterator:
        return PyDictReverseKeyIterator.new(zelf)

    @pyclassmethod(True)
    @staticmethod
    def i__class_getitem__(
        class_: PyTypeRef, args: PyObjectRef, *, vm: VirtualMachine
    ) -> pygenericalias.PyGenericAlias:
        return pygenericalias.PyGenericAlias.new(class_, args, vm)

    @staticmethod
    def inner_cmp(
        zelf: PyDictRef,
        other: PyDictRef,
        op: slot.PyComparisonOp,
        item: bool,
        vm: VirtualMachine,
    ) -> po.PyComparisonValue:
        raise NotImplementedError

    @classmethod
    def as_mapping(
        cls, zelf: PyRef[PyDict], vm: VirtualMachine
    ) -> mapping.PyMappingMethods:
        return cls.MAPPING_METHODS

    @classmethod
    def as_sequence(
        cls, zelf: PyRef[PyDict], vm: VirtualMachine
    ) -> sequence.PySequenceMethods:
        return cls.SEQUENCE_METHODS

    @classmethod
    def iter(cls, zelf: PyRef[PyDict], vm: VirtualMachine) -> PyObjectRef:
        return PyDictKeyIterator.new(zelf).into_ref(vm)

    @classmethod
    def cmp(
        cls,
        zelf: PyRef[PyDict],
        other: PyObjectRef,
        op: slot.PyComparisonOp,
        vm: VirtualMachine,
    ) -> po.PyComparisonValue:
        value = other.downcast_ref(PyDict)
        if value is None:
            return po.PyComparisonValue(None)
        return op.eq_only(
            lambda: PyDict.inner_cmp(zelf, value, slot.PyComparisonOp.Eq, True, vm)
        )


PyDictRef: TypeAlias = "PyRef[PyDict]"


class DictViewMixin(slot.IterableMixin):
    @abstractmethod
    def dict_(self) -> PyDictRef:
        ...

    @classmethod
    @abstractmethod
    def item(
        cls, vm: VirtualMachine, key: PyObjectRef, value: PyObjectRef
    ) -> PyObjectRef:
        ...

    def len(self) -> int:
        return self.dict_()._.len()

    @pymethod(True)
    @classmethod
    def i__repr__(cls, zelf: PyRef, *, vm: VirtualMachine) -> str:
        raise NotImplementedError


class DictIterNextMixin(slot.IterNextMixin, slot.IterNextIterableMixin):
    iterator: Iterator

    @classmethod
    def next_to_pyobj(cls, nv, vm: VirtualMachine) -> PyObjectRef:
        return nv

    @classmethod
    def next(cls: Type[TV], zelf: PyRef[TV], vm: VirtualMachine) -> pyiter.PyIterReturn:
        try:
            item = next(zelf._.iterator, None)
        except RuntimeError as e:
            # TODO: find a better way to do this
            vm.new_runtime_error("dictionary changed size during iteration")
        if item is None:
            return pyiter.PyIterReturnStopIteration(None)
        else:
            return pyiter.PyIterReturnReturn(cls.next_to_pyobj(item, vm))


class ViewSetOps(DictViewMixin, slot.ComparableMixin):
    @staticmethod
    def to_set(zelf: PyRef[ViewSetOps], vm: VirtualMachine) -> pyset.PySetInner:
        raise NotImplementedError

    @pymethod(True)
    @staticmethod
    def i__xor__(
        zelf: PyRef[ViewSetOps], other: arguments.ArgIterable, *, vm: VirtualMachine
    ) -> pyset.PySet:
        return pyset.PySet(
            ViewSetOps.to_set(zelf, vm).symmetric_difference(other, vm=vm)
        )

    @pymethod(True)
    @staticmethod
    def i__rxor__(
        zelf: PyRef[ViewSetOps], other: arguments.ArgIterable, *, vm: VirtualMachine
    ) -> pyset.PySet:
        return ViewSetOps.i__xor__(zelf, other, vm=vm)

    @pymethod(True)
    @staticmethod
    def i__and__(
        zelf: PyRef[ViewSetOps], other: arguments.ArgIterable, *, vm: VirtualMachine
    ) -> pyset.PySet:
        return pyset.PySet(ViewSetOps.to_set(zelf, vm).intersection(other, vm=vm))

    @pymethod(True)
    @staticmethod
    def i__rand__(
        zelf: PyRef[ViewSetOps], other: arguments.ArgIterable, *, vm: VirtualMachine
    ) -> pyset.PySet:
        return ViewSetOps.i__and__(zelf, other, vm=vm)

    @pymethod(True)
    @staticmethod
    def i__or__(
        zelf: PyRef[ViewSetOps], other: arguments.ArgIterable, *, vm: VirtualMachine
    ) -> pyset.PySet:
        return pyset.PySet(ViewSetOps.to_set(zelf, vm).union(other, vm=vm))

    @pymethod(True)
    @staticmethod
    def i__ror__(
        zelf: PyRef[ViewSetOps], other: arguments.ArgIterable, *, vm: VirtualMachine
    ) -> pyset.PySet:
        return ViewSetOps.i__or__(zelf, other, vm=vm)

    @pymethod(True)
    @staticmethod
    def i__sub__(
        zelf: PyRef[ViewSetOps], other: arguments.ArgIterable, *, vm: VirtualMachine
    ) -> pyset.PySet:
        return pyset.PySet(ViewSetOps.to_set(zelf, vm).difference(other, vm=vm))

    @pymethod(True)
    @staticmethod
    def i__rsub__(
        zelf: PyRef[ViewSetOps], other: arguments.ArgIterable, *, vm: VirtualMachine
    ) -> pyset.PySet:
        left = pyset.PySetInner.from_iter(other.iter(vm), vm)
        right = arguments.ArgIterable.try_from_object(vm, ViewSetOps.iter(zelf, vm))
        return pyset.PySet(left.difference(right, vm=vm))

    @pymethod(True)
    @staticmethod
    def isdisjoint(
        zelf: PyRef[ViewSetOps], other: arguments.ArgIterable, *, vm: VirtualMachine
    ) -> bool:
        return ViewSetOps.to_set(zelf, vm).isdisjoint(other, vm=vm)

    @classmethod
    def cmp(
        cls,
        zelf: PyRef[ViewSetOps],
        other: PyObjectRef,
        op: slot.PyComparisonOp,
        vm: VirtualMachine,
    ) -> po.PyComparisonValue:
        raise NotImplementedError


TV = TypeVar("TV", bound="DictIterNextMixin")


@po.pyimpl(
    view_set_opts=True,
    dict_view=True,
    constructor=False,
    comparable=True,
    iterable=True,
    as_sequence=True,
)
@po.pyclass("dict_keys")
@dataclass
class PyDictKeys(po.PyClassImpl, ViewSetOps, slot.IterableMixin, slot.AsSequenceMixin):
    dict: PyDictRef

    SEQUENCE_METHODS: ClassVar = sequence.PySequenceMethods(
        length=lambda s, vm: PyDictKeys.sequence_downcast(s)._.len(),
        contains=lambda s, target, vm: PyDictKeys.sequence_downcast(
            s
        )._.dict._.entries.contains(vm, target),
    )

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.dict_keys_type

    @staticmethod
    def new(dict: PyDictRef) -> PyDictKeys:
        return PyDictKeys(dict)

    @classmethod
    def iter(cls, zelf: PyRef[PyDictKeys], vm: VirtualMachine) -> PyObjectRef:
        return PyDictKeyIterator.new(zelf._.dict).into_ref(vm)

    def dict_(self) -> PyDictRef:
        return self.dict

    @classmethod
    def item(
        cls, vm: VirtualMachine, key: PyObjectRef, value: PyObjectRef
    ) -> PyObjectRef:
        return key

    @pymethod(True)
    def i__reversed__(self, *, vm: VirtualMachine) -> PyDictReverseKeyIterator:
        return PyDictReverseKeyIterator.new(self.dict)

    @classmethod
    def as_sequence(
        cls, zelf: PyRef[PyDictKeys], vm: VirtualMachine
    ) -> sequence.PySequenceMethods:
        return cls.SEQUENCE_METHODS


@po.pyimpl(constructor=False, iter_next=True)
@po.pyclass("dict_keyiterator")
@dataclass
class PyDictKeyIterator(po.PyClassImpl, DictIterNextMixin):
    size: int
    iterator: Iterator[PyObjectRef]

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.dict_keyiterator_type

    @staticmethod
    def new(dict: PyDictRef) -> PyDictKeyIterator:
        return PyDictKeyIterator(
            size=dict._.len(), iterator=iter(dict._.entries.keys())
        )

    @pymethod(True)
    def i__length_hint__(self, *, vm: VirtualMachine) -> int:
        return self.size

    @pymethod(True)
    @staticmethod
    def i__reduce__(
        zelf: PyRef[PyDictKeyIterator], *, vm: VirtualMachine
    ) -> PyObjectRef:
        raise NotImplementedError


@po.pyimpl(constructor=False, iter_next=True)
@po.pyclass("dict_reversekeyiterator")
@dataclass
class PyDictReverseKeyIterator(po.PyClassImpl, DictIterNextMixin):
    size: int
    iterator: Iterator[PyObjectRef]

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.dict_reversekeyiterator_type

    @staticmethod
    def new(dict: PyDictRef) -> PyDictReverseKeyIterator:
        return PyDictReverseKeyIterator(
            size=dict._.len(), iterator=reversed(dict._.entries.keys())
        )

    @pymethod(True)
    def i__length_hint__(self, *, vm: VirtualMachine) -> int:
        return self.size


@po.pyimpl(dict_view=True, constructor=False, iterable=True, as_sequence=True)
@po.pyclass("dict_values")
@dataclass
class PyDictValues(
    po.PyClassImpl, DictViewMixin, slot.IterableMixin, slot.AsSequenceMixin
):
    dict: PyDictRef

    SEQUENCE_METHODS: ClassVar = sequence.PySequenceMethods(
        length=lambda s, vm: PyDictValues.sequence_downcast(s)._.len()
    )

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.dict_values_type

    @staticmethod
    def new(dict: PyDictRef) -> PyDictValues:
        return PyDictValues(dict)

    @classmethod
    def iter(cls, zelf: PyRef[PyDictValues], vm: VirtualMachine) -> PyDictValueIterator:
        return PyDictValueIterator.new(zelf._.dict)

    def dict_(self) -> PyDictRef:
        return self.dict

    @classmethod
    def item(
        cls, vm: VirtualMachine, key: PyObjectRef, value: PyObjectRef
    ) -> PyObjectRef:
        return value

    @pymethod(True)
    def i__reversed__(self, *, vm: VirtualMachine) -> PyDictReverseValueIterator:
        return PyDictReverseValueIterator.new(self.dict)

    @classmethod
    def as_sequence(
        cls, zelf: PyRef[PyDictValues], vm: VirtualMachine
    ) -> sequence.PySequenceMethods:
        return cls.SEQUENCE_METHODS


@po.pyimpl(constructor=False, iter_next=True)
@po.pyclass("dict_valueiterator")
@dataclass
class PyDictValueIterator(po.PyClassImpl, DictIterNextMixin):
    size: int
    iterator: Iterator[PyObjectRef]

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.dict_valueiterator_type

    @staticmethod
    def new(dict: PyDictRef) -> PyDictValueIterator:
        return PyDictValueIterator(
            size=dict._.len(), iterator=iter(dict._.entries.values())
        )

    @pymethod(True)
    def i__length_hint__(self, *, vm: VirtualMachine) -> int:
        return self.size

    @pymethod(True)
    @staticmethod
    def i__reduce__(
        zelf: PyRef[PyDictValueIterator], *, vm: VirtualMachine
    ) -> PyObjectRef:
        raise NotImplementedError


@po.pyimpl(constructor=False, iter_next=True)
@po.pyclass("dict_reversevalueiterator")
@dataclass
class PyDictReverseValueIterator(po.PyClassImpl, DictIterNextMixin):
    size: int
    iterator: Iterator[PyObjectRef]

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.dict_reversevalueiterator_type

    @staticmethod
    def new(dict: PyDictRef) -> PyDictReverseValueIterator:
        return PyDictReverseValueIterator(dict._.len(), iter(dict._.entries.values()))

    @pymethod(True)
    def i__length_hint__(self, *, vm: VirtualMachine) -> int:
        return self.size


@po.pyimpl(
    view_set_opts=True,
    dict_view=True,
    constructor=False,
    comparable=True,
    iterable=True,
    as_sequence=True,
)
@po.pyclass("dict_items")
@dataclass
class PyDictItems(po.PyClassImpl, slot.AsSequenceMixin, ViewSetOps, slot.IterableMixin):
    dict: PyDictRef

    SEQUENCE_METHODS: ClassVar[sequence.PySequenceMethods] = sequence.PySequenceMethods(
        length=lambda s, vm: PyDictItems.sequence_downcast(s)._.len(),
        contains=lambda s, target, vm: PyDictItems.sequence_downcast(
            s
        )._.dict._.entries.contains(vm, target),
    )

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.dict_items_type

    @staticmethod
    def new(dict: PyDictRef) -> PyDictItems:
        return PyDictItems(dict)

    def dict_(self) -> PyDictRef:
        return self.dict

    @classmethod
    def item(
        cls, vm: VirtualMachine, key: PyObjectRef, value: PyObjectRef
    ) -> PyObjectRef:
        return vm.ctx.new_tuple([key, value])

    @pymethod(True)
    def i__reversed__(self, *, vm: VirtualMachine) -> PyDictReverseItemIterator:
        return PyDictReverseItemIterator.new(self.dict)

    @classmethod
    def iter(cls, zelf: PyRef[PyDictItems], vm: VirtualMachine) -> PyObjectRef:
        return PyDictItemIterator.new(zelf._.dict).into_ref(vm)

    @classmethod
    def as_sequence(
        cls, zelf: PyRef[PyDictItems], vm: VirtualMachine
    ) -> sequence.PySequenceMethods:
        return cls.SEQUENCE_METHODS


@po.pyimpl(constructor=False, iter_next=True)
@po.pyclass("dict_itemiterator")
@dataclass
class PyDictItemIterator(po.PyClassImpl, DictIterNextMixin):
    size: int
    internal: pyiter.PositionIterInternal[PyDictRef]
    iterator: Iterator[tuple[PyObjectRef, PyObjectRef]]

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.dict_itemiterator_type

    @staticmethod
    def new(dict: PyDictRef) -> PyDictItemIterator:
        return PyDictItemIterator(
            dict._.len(),
            pyiter.PositionIterInternal.new(dict, 0),
            iterator=iter(dict._.entries.items()),
        )

    @pymethod(True)
    def i__length_hint__(self, *, vm: VirtualMachine) -> int:
        return self.size

    @classmethod
    def next_to_pyobj(
        cls, nv: tuple[PyObjectRef, PyObjectRef], vm: VirtualMachine
    ) -> PyObjectRef:
        return vm.ctx.new_tuple(list(nv))


@po.pyimpl(constructor=False, iter_next=True)
@po.pyclass("dict_reverseitemiterator")
@dataclass
class PyDictReverseItemIterator(po.PyClassImpl, DictIterNextMixin):
    size: int
    iterator: Iterator[tuple[PyObjectRef, PyObjectRef]]

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.dict_reverseitemiterator_type

    @staticmethod
    def new(dict: PyDictRef) -> PyDictReverseItemIterator:
        return PyDictReverseItemIterator(
            dict._.len(),
            iterator=reversed(dict._.entries.items()),
        )

    @pymethod(True)
    def i__length_hint__(self, *, vm: VirtualMachine) -> int:
        return self.size

    @classmethod
    def next_to_pyobj(
        cls, nv: tuple[PyObjectRef, PyObjectRef], vm: VirtualMachine
    ) -> PyObjectRef:
        return vm.ctx.new_tuple(list(nv))


def init(context: PyContext) -> None:
    PyDict.extend_class(context, context.types.dict_type)

    PyDictKeys.extend_class(context, context.types.dict_keys_type)
    PyDictKeyIterator.extend_class(context, context.types.dict_keyiterator_type)
    PyDictReverseKeyIterator.extend_class(
        context, context.types.dict_reversekeyiterator_type
    )

    PyDictValues.extend_class(context, context.types.dict_values_type)
    PyDictValueIterator.extend_class(context, context.types.dict_valueiterator_type)
    PyDictReverseValueIterator.extend_class(
        context, context.types.dict_reversevalueiterator_type
    )

    PyDictItems.extend_class(context, context.types.dict_items_type)
    PyDictItemIterator.extend_class(context, context.types.dict_itemiterator_type)
    PyDictReverseItemIterator.extend_class(
        context, context.types.dict_reverseitemiterator_type
    )
