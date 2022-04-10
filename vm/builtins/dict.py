from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar, Iterable, Optional, TypeAlias


if TYPE_CHECKING:
    from vm.builtins.pytype import PyTypeRef
    from vm.pyobject import PyContext
    from vm.pyobjectrc import PyObjectRef, PyRef
    from vm.vm import VirtualMachine

from vm.dictdatatype import Dict as DictContentType
import vm.pyobject as po
import vm.pyobjectrc as prc
import vm.protocol.mapping as mapping


@po.tp_flags(basetype=True)
@po.pyimpl(
    as_mapping=True, hashable=True, comparable=True, iterable=True, as_sequence=True
)
@po.pyclass("dict")
@dataclass
class PyDict(po.TryFromObjectMixin, po.PyValueMixin, po.PyClassImpl):
    entries: DictContentType

    MAPPING_METHODS: ClassVar = mapping.PyMappingMethods(
        length=None, subscript=None, ass_subscript=lambda m, k, v, vm: print(v)
    )

    @staticmethod
    def new_ref(ctx: PyContext) -> PyDictRef:
        return prc.PyRef.new_ref(PyDict(DictContentType()), ctx.types.dict_type, None)

    @staticmethod
    def class_(vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.dict_type

    def get_item_opt(
        self, key: PyObjectRef, vm: VirtualMachine
    ) -> Optional[PyObjectRef]:
        self.entries.get(vm, key)

    def contains_key(self, key: PyObjectRef, vm: VirtualMachine) -> bool:
        return self.entries.contains(vm, key)

    def set_item(
        self, key: PyObjectRef, value: PyObjectRef, vm: VirtualMachine
    ) -> None:
        self.entries.insert(vm, key, value)

    def items(self) -> Iterable[tuple[PyObjectRef, PyObjectRef]]:
        return self.entries.items()

    def get_chain(
        self, other: PyDict, key: PyObjectRef, vm: VirtualMachine
    ) -> Optional[PyObjectRef]:
        return self.entries.get_chain(vm, other.entries, key)


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
class PyDictKeys(po.PyValueMixin, po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.dict_keys_type


@po.pyimpl(constructor=True, iter_next=True)
@po.pyclass("dict_keyiterator")
@dataclass
class PyDictKeyIterator(po.PyValueMixin, po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.dict_keyiterator_type


@po.pyimpl(constructor=True, iter_next=True)
@po.pyclass("dict_reversekeyiterator")
@dataclass
class PyDictReverseKeyIterator(po.PyValueMixin, po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.dict_reversekeyiterator_type


@po.pyimpl(dict_view=True, constructor=True, iterable=True, as_sequence=True)
@po.pyclass("dict_values")
@dataclass
class PyDictValues(po.PyValueMixin, po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.dict_values_type


@po.pyimpl(constructor=True, iter_next=True)
@po.pyclass("dict_valueiterator")
@dataclass
class PyDictValueIterator(po.PyValueMixin, po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.dict_valueiterator_type


@po.pyimpl(constructor=True, iter_next=True)
@po.pyclass("dict_reversevalueiterator")
@dataclass
class PyDictReverseValueIterator(po.PyValueMixin, po.PyClassImpl):
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
class PyDictItems(po.PyValueMixin, po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.dict_items_type


@po.pyimpl(constructor=True, iter_next=True)
@po.pyclass("dict_itemiterator")
@dataclass
class PyDictItemIterator(po.PyValueMixin, po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.dict_keys_type


@po.pyimpl(constructor=True, iter_next=True)
@po.pyclass("dict_reverseitemiterator")
@dataclass
class PyDictReverseItemIterator(po.PyValueMixin, po.PyClassImpl):
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
