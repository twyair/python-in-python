from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import vm.pyobjectrc

if TYPE_CHECKING:
    from vm.builtins.pytype import PyTypeRef
    from vm.pyobject import PyContext

import vm.builtins.asyncgenerator
import vm.builtins.builtinfunc
import vm.builtins.bytearray
import vm.builtins.bytes
import vm.builtins.classmethod
import vm.builtins.code
import vm.builtins.complex
import vm.builtins.coroutine
import vm.builtins.dict
import vm.builtins.enumerate
import vm.builtins.filter
import vm.builtins.float
import vm.builtins.frame
import vm.builtins.function
import vm.builtins.generator
import vm.builtins.genericalias
import vm.builtins.getset
import vm.builtins.int
import vm.builtins.iter
import vm.builtins.list
import vm.builtins.map
import vm.builtins.mappingproxy
import vm.builtins.memory
import vm.builtins.module
import vm.builtins.namespace
import vm.builtins.object
import vm.builtins.property
import vm.builtins.pybool
import vm.builtins.pystr
import vm.builtins.pysuper
import vm.builtins.pytype
import vm.builtins.pyunion
import vm.builtins.range
import vm.builtins.set
import vm.builtins.singletons
import vm.builtins.slice
import vm.builtins.staticmethod
import vm.builtins.traceback
import vm.builtins.tuple
import vm.builtins.weakproxy
import vm.builtins.weakref
import vm.builtins.zip

import vm.pyobject
import vm.frame


@dataclass
class TypeZoo:
    async_generator: PyTypeRef
    async_generator_asend: PyTypeRef
    async_generator_athrow: PyTypeRef
    async_generator_wrapped_value: PyTypeRef
    bytes_type: PyTypeRef
    bytes_iterator_type: PyTypeRef
    bytearray_type: PyTypeRef
    bytearray_iterator_type: PyTypeRef
    bool_type: PyTypeRef
    callable_iterator: PyTypeRef
    cell_type: PyTypeRef
    classmethod_type: PyTypeRef
    code_type: PyTypeRef
    coroutine_type: PyTypeRef
    coroutine_wrapper_type: PyTypeRef
    dict_type: PyTypeRef
    enumerate_type: PyTypeRef
    filter_type: PyTypeRef
    float_type: PyTypeRef
    frame_type: PyTypeRef
    frozenset_type: PyTypeRef
    generator_type: PyTypeRef
    int_type: PyTypeRef
    iter_type: PyTypeRef
    reverse_iter_type: PyTypeRef
    complex_type: PyTypeRef
    list_type: PyTypeRef
    list_iterator_type: PyTypeRef
    list_reverseiterator_type: PyTypeRef
    str_iterator_type: PyTypeRef
    dict_keyiterator_type: PyTypeRef
    dict_reversekeyiterator_type: PyTypeRef
    dict_valueiterator_type: PyTypeRef
    dict_reversevalueiterator_type: PyTypeRef
    dict_itemiterator_type: PyTypeRef
    dict_reverseitemiterator_type: PyTypeRef
    dict_keys_type: PyTypeRef
    dict_values_type: PyTypeRef
    dict_items_type: PyTypeRef
    map_type: PyTypeRef
    memoryview_type: PyTypeRef
    tuple_type: PyTypeRef
    tuple_iterator_type: PyTypeRef
    set_type: PyTypeRef
    set_iterator_type: PyTypeRef
    staticmethod_type: PyTypeRef
    super_type: PyTypeRef
    str_type: PyTypeRef
    range_type: PyTypeRef
    range_iterator_type: PyTypeRef
    longrange_iterator_type: PyTypeRef
    slice_type: PyTypeRef
    type_type: PyTypeRef
    zip_type: PyTypeRef
    function_type: PyTypeRef
    builtin_function_or_method_type: PyTypeRef
    method_descriptor_type: PyTypeRef
    property_type: PyTypeRef
    getset_type: PyTypeRef
    module_type: PyTypeRef
    namespace_type: PyTypeRef
    bound_method_type: PyTypeRef
    weakref_type: PyTypeRef
    weakproxy_type: PyTypeRef
    mappingproxy_type: PyTypeRef
    traceback_type: PyTypeRef
    object_type: PyTypeRef
    ellipsis_type: PyTypeRef
    none_type: PyTypeRef
    not_implemented_type: PyTypeRef
    generic_alias_type: PyTypeRef
    union_type: PyTypeRef

    @staticmethod
    def init() -> TypeZoo:
        type_type, object_type, weakref_type = vm.pyobjectrc.init_type_hierarchy()

        return TypeZoo(
            type_type=vm.builtins.pytype.PyType.init_manually(type_type),
            object_type=vm.builtins.object.PyBaseObject.init_manually(object_type),
            weakref_type=vm.pyobject.PyWeak.init_manually(weakref_type),
            async_generator=vm.builtins.asyncgenerator.PyAsyncGen.init_bare_type(),
            async_generator_asend=vm.builtins.asyncgenerator.PyAsyncGenASend.init_bare_type(),
            async_generator_athrow=vm.builtins.asyncgenerator.PyAsyncGenAThrow.init_bare_type(),
            async_generator_wrapped_value=vm.builtins.asyncgenerator.PyAsyncGenWrappedValue.init_bare_type(),
            bytes_type=vm.builtins.bytes.PyBytes.init_bare_type(),
            bytes_iterator_type=vm.builtins.bytes.PyBytesIterator.init_bare_type(),
            bytearray_type=vm.builtins.bytearray.PyByteArray.init_bare_type(),
            bytearray_iterator_type=vm.builtins.bytearray.PyByteArrayIterator.init_bare_type(),
            bool_type=vm.builtins.pybool.PyBool.init_bare_type(),
            callable_iterator=vm.builtins.iter.PyCallableIterator.init_bare_type(),
            cell_type=vm.builtins.function.PyCell.init_bare_type(),
            classmethod_type=vm.builtins.classmethod.PyClassMethod.init_bare_type(),
            code_type=vm.builtins.code.PyCode.init_bare_type(),
            coroutine_type=vm.builtins.coroutine.PyCoroutine.init_bare_type(),
            coroutine_wrapper_type=vm.builtins.coroutine.PyCoroutineWrapper.init_bare_type(),
            dict_type=vm.builtins.dict.PyDict.init_bare_type(),
            enumerate_type=vm.builtins.enumerate.PyEnumerate.init_bare_type(),
            filter_type=vm.builtins.filter.PyFilter.init_bare_type(),
            float_type=vm.builtins.float.PyFloat.init_bare_type(),
            frame_type=vm.frame.Frame.init_bare_type(),
            frozenset_type=vm.builtins.set.PyFrozenSet.init_bare_type(),
            generator_type=vm.builtins.generator.PyGenerator.init_bare_type(),
            int_type=vm.builtins.int.PyInt.init_bare_type(),
            iter_type=vm.builtins.iter.PySequenceIterator.init_bare_type(),
            reverse_iter_type=vm.builtins.enumerate.PyReverseSequenceIterator.init_bare_type(),
            complex_type=vm.builtins.complex.PyComplex.init_bare_type(),
            list_type=vm.builtins.list.PyList.init_bare_type(),
            list_iterator_type=vm.builtins.list.PyListIterator.init_bare_type(),
            list_reverseiterator_type=vm.builtins.list.PyListReverseIterator.init_bare_type(),
            str_iterator_type=vm.builtins.pystr.PyStrIterator.init_bare_type(),
            dict_keyiterator_type=vm.builtins.dict.PyDictKeyIterator.init_bare_type(),
            dict_reversekeyiterator_type=vm.builtins.dict.PyDictReverseKeyIterator.init_bare_type(),
            dict_valueiterator_type=vm.builtins.dict.PyDictValueIterator.init_bare_type(),
            dict_reversevalueiterator_type=vm.builtins.dict.PyDictReverseValueIterator.init_bare_type(),
            dict_itemiterator_type=vm.builtins.dict.PyDictItemIterator.init_bare_type(),
            dict_reverseitemiterator_type=vm.builtins.dict.PyDictReverseItemIterator.init_bare_type(),
            dict_keys_type=vm.builtins.dict.PyDictKeys.init_bare_type(),
            dict_values_type=vm.builtins.dict.PyDictValues.init_bare_type(),
            dict_items_type=vm.builtins.dict.PyDictItems.init_bare_type(),
            map_type=vm.builtins.map.PyMap.init_bare_type(),
            memoryview_type=vm.builtins.memory.PyMemoryView.init_bare_type(),
            tuple_type=vm.builtins.tuple.PyTuple.init_bare_type(),
            tuple_iterator_type=vm.builtins.tuple.PyTupleIterator.init_bare_type(),
            set_type=vm.builtins.set.PySet.init_bare_type(),
            set_iterator_type=vm.builtins.set.PySetIterator.init_bare_type(),
            staticmethod_type=vm.builtins.staticmethod.PyStaticMethod.init_bare_type(),
            super_type=vm.builtins.pysuper.PySuper.init_bare_type(),
            str_type=vm.builtins.pystr.PyStr.init_bare_type(),
            range_type=vm.builtins.range.PyRange.init_bare_type(),
            range_iterator_type=vm.builtins.range.PyRangeIterator.init_bare_type(),
            longrange_iterator_type=vm.builtins.range.PyLongRangeIterator.init_bare_type(),
            slice_type=vm.builtins.slice.PySlice.init_bare_type(),
            zip_type=vm.builtins.zip.PyZip.init_bare_type(),
            function_type=vm.builtins.function.PyFunction.init_bare_type(),
            builtin_function_or_method_type=vm.builtins.builtinfunc.PyBuiltinFunction.init_bare_type(),
            method_descriptor_type=vm.builtins.builtinfunc.PyBuiltinMethod.init_bare_type(),
            property_type=vm.builtins.property.PyProperty.init_bare_type(),
            getset_type=vm.builtins.getset.PyGetSet.init_bare_type(),
            module_type=vm.builtins.module.PyModule.init_bare_type(),
            namespace_type=vm.builtins.namespace.PyNamespace.init_bare_type(),
            bound_method_type=vm.builtins.function.PyBoundMethod.init_bare_type(),
            weakproxy_type=vm.builtins.weakproxy.PyWeakProxy.init_bare_type(),
            mappingproxy_type=vm.builtins.mappingproxy.PyMappingProxy.init_bare_type(),
            traceback_type=vm.builtins.traceback.PyTraceback.init_bare_type(),
            ellipsis_type=vm.builtins.slice.PyEllipsis.init_bare_type(),
            none_type=vm.builtins.singletons.PyNone.init_bare_type(),
            not_implemented_type=vm.builtins.singletons.PyNotImplemented.init_bare_type(),
            generic_alias_type=vm.builtins.genericalias.PyGenericAlias.init_bare_type(),
            union_type=vm.builtins.pyunion.PyUnion.init_bare_type(),
        )

    @staticmethod
    def extend(context: PyContext) -> None:
        vm.builtins.pytype.init(context)
        vm.builtins.object.init(context)
        vm.builtins.weakref.init(context)
        vm.builtins.list.init(context)
        vm.builtins.set.init(context)
        vm.builtins.tuple.init(context)
        vm.builtins.dict.init(context)
        vm.builtins.builtinfunc.init(context)
        vm.builtins.function.init(context)
        vm.builtins.staticmethod.init(context)
        vm.builtins.classmethod.init(context)
        vm.builtins.generator.init(context)
        vm.builtins.coroutine.init(context)
        vm.builtins.asyncgenerator.init(context)
        vm.builtins.int.init(context)
        vm.builtins.float.init(context)
        vm.builtins.complex.init(context)
        vm.builtins.bytes.init(context)
        vm.builtins.bytearray.init(context)
        vm.builtins.property.init(context)
        vm.builtins.getset.init(context)
        vm.builtins.memory.init(context)
        vm.builtins.pystr.init(context)
        vm.builtins.range.init(context)
        vm.builtins.slice.init(context)
        vm.builtins.pysuper.init(context)
        vm.builtins.iter.init(context)
        vm.builtins.enumerate.init(context)
        vm.builtins.filter.init(context)
        vm.builtins.map.init(context)
        vm.builtins.zip.init(context)
        vm.builtins.pybool.init(context)
        vm.builtins.code.init(context)
        vm.builtins.frame.init(context)
        vm.builtins.weakproxy.init(context)
        vm.builtins.singletons.init(context)
        vm.builtins.module.init(context)
        vm.builtins.namespace.init(context)
        vm.builtins.mappingproxy.init(context)
        vm.builtins.traceback.init(context)
        vm.builtins.genericalias.init(context)
        vm.builtins.pyunion.init(context)
