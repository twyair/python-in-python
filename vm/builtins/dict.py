from __future__ import annotations
from abc import ABC, abstractmethod

from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar, Iterator, Optional, Type, TypeAlias, TypeVar

if TYPE_CHECKING:
    from vm.builtins.pytype import PyTypeRef
    from vm.pyobject import PyContext
    from vm.pyobjectrc import PyObjectRef, PyRef
    from vm.vm import VirtualMachine

import vm.function_ as vm_function_
import vm.protocol.mapping as mapping
import vm.protocol.sequence as sequence
import vm.builtins.iter as pyiter
import vm.pyobject as po
import vm.pyobjectrc as prc
import vm.types.slot as slot
from vm.dictdatatype import Dict as DictContentType

from common.deco import pymethod


@po.tp_flags(basetype=True)
@po.pyimpl(
    as_mapping=True, hashable=True, comparable=True, iterable=True, as_sequence=True
)
@po.pyclass("dict")
@dataclass
class PyDict(po.PyClassImpl, slot.AsMappingMixin, slot.IterableMixin):
    entries: DictContentType

    MAPPING_METHODS: ClassVar = mapping.PyMappingMethods(
        length=lambda m, vm: PyDict.mapping_downcast(m)._.len(),
        subscript=lambda m, k, vm: PyDict.mapping_downcast(m)._.get_item(k, vm),
        ass_subscript=lambda m, k, v, vm: PyDict.ass_subscript(m, k, v, vm),
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

    def len(self) -> int:
        return self.entries.len()

    @pymethod(True)
    def i__len__(self, vm: VirtualMachine) -> PyObjectRef:
        return vm.ctx.new_int(self.len())

    @pymethod(True)
    @staticmethod
    def items(zelf: PyRef[PyDict], vm: VirtualMachine) -> PyObjectRef:
        return PyDictItems.new(zelf).into_ref(vm)

    @pymethod(True)
    def i__setitem__(
        self, key: PyObjectRef, value: PyObjectRef, vm: VirtualMachine
    ) -> None:
        self.inner_setitem(key, value, vm)

    @pymethod(True)
    def i__getitem__(self, key: PyObjectRef, vm: VirtualMachine) -> PyObjectRef:
        return self.inner_getitem(key, vm)

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

    @classmethod
    def as_mapping(
        cls, zelf: PyRef[PyDict], vm: VirtualMachine
    ) -> mapping.PyMappingMethods:
        return cls.MAPPING_METHODS

    @classmethod
    def iter(cls, zelf: PyRef[PyDict], vm: VirtualMachine) -> PyObjectRef:
        return PyDictKeyIterator.new(zelf).into_ref(vm)


PyDictRef: TypeAlias = "PyRef[PyDict]"


class DictViewMixin(ABC):
    @abstractmethod
    def dict_(self) -> PyDictRef:
        ...

    def len(self) -> int:
        return self.dict_()._.len()


class DictIterNextMixin(slot.IterNextMixin, slot.IterNextIterableMixin):
    iterator: Iterator
    # @abstractmethod
    # def iterator_(self) -> Iterator:
    #     ...

    @classmethod
    @abstractmethod
    def next_to_pyobj(cls, nv, vm: VirtualMachine) -> PyObjectRef:
        ...

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
class PyDictKeys(po.PyClassImpl, slot.IterableMixin):
    dict: PyDictRef

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.dict_keys_type

    @staticmethod
    def new(dict: PyDictRef) -> PyDictKeys:
        return PyDictKeys(dict)

    # TODO: impl as_sequence, ...
    @classmethod
    def iter(cls, zelf: PyRef[PyDictKeys], vm: VirtualMachine) -> PyObjectRef:
        return PyDictKeyIterator.new(zelf._.dict).into_ref(vm)


@po.pyimpl(constructor=False, iter_next=True)
@po.pyclass("dict_keyiterator")
@dataclass
class PyDictKeyIterator(po.PyClassImpl, DictIterNextMixin):
    size: int
    internal: pyiter.PositionIterInternal[PyDictRef]
    iterator: Iterator[tuple[PyObjectRef, PyObjectRef]]

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.dict_keyiterator_type

    @staticmethod
    def new(dict: PyDictRef) -> PyDictKeyIterator:
        return PyDictKeyIterator(
            size=dict._.len(), internal="TODO", iterator=iter(dict._.entries.keys())
        )  # TODO

    @classmethod
    def next_to_pyobj(cls, nv: PyObjectRef, vm: VirtualMachine) -> PyObjectRef:
        return nv


@po.pyimpl(constructor=False, iter_next=True)
@po.pyclass("dict_reversekeyiterator")
@dataclass
class PyDictReverseKeyIterator(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.dict_reversekeyiterator_type

    # TODO: impl iter_next, ...


@po.pyimpl(dict_view=True, constructor=True, iterable=True, as_sequence=True)
@po.pyclass("dict_values")
@dataclass
class PyDictValues(po.PyClassImpl):
    dict: PyDictRef

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.dict_values_type

    @staticmethod
    def new(dict: PyDictRef) -> PyDictValues:
        return PyDictValues(dict)

    # TODO: impl as_sequence, ...


@po.pyimpl(constructor=True, iter_next=True)
@po.pyclass("dict_valueiterator")
@dataclass
class PyDictValueIterator(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.dict_valueiterator_type

    # TODO: impl iter_next, ...


@po.pyimpl(constructor=True, iter_next=True)
@po.pyclass("dict_reversevalueiterator")
@dataclass
class PyDictReverseValueIterator(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.dict_reversevalueiterator_type

    # TODO: impl iter_next, ...


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
class PyDictItems(
    po.PyClassImpl, slot.AsSequenceMixin, DictViewMixin, slot.IterableMixin
):
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

    @classmethod
    def next_to_pyobj(
        cls, nv: tuple[PyObjectRef, PyObjectRef], vm: VirtualMachine
    ) -> PyObjectRef:
        return vm.ctx.new_tuple(list(nv))


@po.pyimpl(constructor=True, iter_next=True)
@po.pyclass("dict_reverseitemiterator")
@dataclass
class PyDictReverseItemIterator(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.dict_reverseitemiterator_type


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
