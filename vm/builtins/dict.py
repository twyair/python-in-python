from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar, Iterator, Optional, TypeAlias

if TYPE_CHECKING:
    from vm.builtins.pytype import PyTypeRef
    from vm.pyobject import PyContext
    from vm.pyobjectrc import PyObjectRef, PyRef
    from vm.vm import VirtualMachine

import vm.function_ as vm_function_
import vm.protocol.mapping as mapping
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
class PyDict(po.PyClassImpl, slot.AsMappingMixin):
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


PyDictRef: TypeAlias = "PyRef[PyDict]"


@po.pyimpl(
    view_set_opts=True,
    dict_view=True,
    constructor=True,
    comparable=True,
    iterable=True,
    as_sequence=True,
)
@po.pyclass("dict_keys")
@dataclass
class PyDictKeys(po.PyClassImpl):
    dict: PyDictRef

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.dict_keys_type

    @staticmethod
    def new(dict: PyDictRef) -> PyDictKeys:
        return PyDictKeys(dict)


@po.pyimpl(constructor=True, iter_next=True)
@po.pyclass("dict_keyiterator")
@dataclass
class PyDictKeyIterator(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.dict_keyiterator_type


@po.pyimpl(constructor=True, iter_next=True)
@po.pyclass("dict_reversekeyiterator")
@dataclass
class PyDictReverseKeyIterator(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.dict_reversekeyiterator_type


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


@po.pyimpl(constructor=True, iter_next=True)
@po.pyclass("dict_valueiterator")
@dataclass
class PyDictValueIterator(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.dict_valueiterator_type


@po.pyimpl(constructor=True, iter_next=True)
@po.pyclass("dict_reversevalueiterator")
@dataclass
class PyDictReverseValueIterator(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.dict_reversevalueiterator_type


@po.pyimpl(
    view_set_opts=True,
    dict_view=True,
    constructor=True,
    comparable=True,
    iterable=True,
    as_sequence=True,
)
@po.pyclass("dict_items")
@dataclass
class PyDictItems(po.PyClassImpl):
    dict: PyDictRef

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.dict_items_type

    @staticmethod
    def new(dict: PyDictRef) -> PyDictItems:
        return PyDictItems(dict)


@po.pyimpl(constructor=True, iter_next=True)
@po.pyclass("dict_itemiterator")
@dataclass
class PyDictItemIterator(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.dict_keys_type


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
