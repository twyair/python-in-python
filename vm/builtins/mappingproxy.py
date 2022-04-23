from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar, Optional, Union
from common.deco import pyclassmethod, pymethod
from vm.pyobjectrc import PyObject, pyref_type_error

if TYPE_CHECKING:
    from vm.pyobject import PyContext
    from vm.pyobjectrc import PyObjectRef, PyRef
    from typing import Union
    from vm.builtins.pytype import PyTypeRef
    from vm.vm import VirtualMachine
import vm.pyobject as po
import vm.builtins.pystr as pystr
import vm.builtins.dict as pydict
import vm.builtins.list as pylist
import vm.builtins.tuple as pytuple
import vm.builtins.genericalias as pygenericalias
import vm.protocol.sequence as sequence
import vm.protocol.mapping as vmapping
import vm.function_ as fn
import vm.types.slot as slot
from common import to_opt


@po.pyimpl(constructor=True, iterable=True, as_mapping=True, as_sequence=True)
@po.pyclass("mappingproxy")
@dataclass
class PyMappingProxy(
    po.PyClassImpl,
    slot.IterableMixin,
    slot.AsMappingMixin,
    slot.AsSequenceMixin,
    slot.ConstructorMixin,
):
    mapping: MappingProxyInner

    MAPPING_METHODS: ClassVar[vmapping.PyMappingMethods] = vmapping.PyMappingMethods(
        length=None,
        subscript=lambda m, needle, vm: PyMappingProxy.mapping_downcast(
            m
        )._.i__getitem__(needle, vm=vm),
        ass_subscript=None,
    )

    SEQUENCE_METHODS: ClassVar[sequence.PySequenceMethods] = sequence.PySequenceMethods(
        contains=lambda s, target, vm: PyMappingProxy.sequence_downcast(s)._._contains(
            target, vm
        )
    )

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.mappingproxy_type

    @staticmethod
    def new(class_: PyTypeRef) -> PyMappingProxy:
        return PyMappingProxy(MappingProxyClass(class_))

    def get_inner(self, key: PyObjectRef, vm: VirtualMachine) -> Optional[PyObjectRef]:
        if isinstance(self.mapping, MappingProxyClass):
            return self.mapping.value._.attributes.get(
                pystr.PyStr.try_from_object(vm, key)._.as_str(), None
            )
        else:
            return to_opt(lambda: self.mapping.value.get_item(key, vm))

    @pymethod(True)
    def get(
        self,
        key: PyObjectRef,
        default: Optional[PyObjectRef] = None,
        *,
        vm: VirtualMachine,
    ) -> Optional[PyObjectRef]:
        v = self.get_inner(key, vm)
        if v is None:
            return default
        else:
            return v

    @pymethod(True)
    def i__getitem__(self, key: PyObjectRef, *, vm: VirtualMachine) -> PyObjectRef:
        if (v := self.get_inner(key, vm)) is not None:
            return v
        vm.new_key_error(key)

    def _contains(self, key: PyObject, vm: VirtualMachine) -> bool:
        if isinstance(self.mapping, MappingProxyClass):
            key_ = key.payload_(pystr.PyStr)
            if key_ is None:
                pyref_type_error(vm, pystr.PyStr.class_(vm), key)
            return self.mapping.value._.attributes.contains_key(key_.as_str())
        else:
            return sequence.PySequence.from_pyobj(self.mapping.value).contains(key, vm)

    @pymethod(True)
    def i__contains__(self, key: PyObjectRef, *, vm: VirtualMachine) -> bool:
        return self._contains(key, vm)

    def __get_obj(self, vm: VirtualMachine) -> PyObjectRef:
        if isinstance(self.mapping, MappingProxyDict):
            return self.mapping.value
        else:
            return pydict.PyDict.from_attributes(
                self.mapping.value._.attributes, vm
            ).into_ref(vm)

    @pymethod(True)
    def items(self, *, vm: VirtualMachine) -> PyObjectRef:
        return vm.call_method(self.__get_obj(vm), "items", fn.FuncArgs())

    @pymethod(True)
    def keys(self, *, vm: VirtualMachine) -> PyObjectRef:
        return vm.call_method(self.__get_obj(vm), "keys", fn.FuncArgs())

    @pymethod(True)
    def values(self, *, vm: VirtualMachine) -> PyObjectRef:
        return vm.call_method(self.__get_obj(vm), "values", fn.FuncArgs())

    @pymethod(True)
    def copy(self, *, vm: VirtualMachine) -> PyObjectRef:
        if isinstance(self.mapping, MappingProxyDict):
            return vm.call_method(self.mapping.value, "copy", fn.FuncArgs())
        else:
            return pydict.PyDict.from_attributes(
                self.mapping.value._.attributes, vm
            ).into_ref(vm)

    @pymethod(True)
    def i__repr__(self, *, vm: VirtualMachine) -> str:
        return "mappingproxy({})".format(self.__get_obj(vm).repr(vm)._.as_str())

    @pyclassmethod(True)
    @staticmethod
    def i__class_getitem__(
        class_: PyTypeRef, args: PyObjectRef, *, vm: VirtualMachine
    ) -> pygenericalias.PyGenericAlias:
        return pygenericalias.PyGenericAlias.new(class_, args, vm)

    @classmethod
    def as_sequence(
        cls, zelf: PyRef[PyMappingProxy], vm: VirtualMachine
    ) -> sequence.PySequenceMethods:
        return cls.SEQUENCE_METHODS

    @classmethod
    def as_mapping(
        cls, zelf: PyRef[PyMappingProxy], vm: VirtualMachine
    ) -> vmapping.PyMappingMethods:
        return cls.MAPPING_METHODS

    @classmethod
    def py_new(
        cls, class_: PyTypeRef, fargs: fn.FuncArgs, /, vm: VirtualMachine
    ) -> PyObjectRef:
        arg: PyObjectRef = fargs.bind(args_py_new).arguments["mapping"]
        if (
            not vmapping.PyMapping.from_pyobj(arg).check(vm)
            or arg.payload_if_subclass(pylist.PyList, vm) is not None
            or arg.payload_if_subclass(pytuple.PyTuple, vm) is not None
        ):
            vm.new_type_error(
                "mappingproxy() argument must be a mapping, not {}".format(
                    arg.class_()._.name()
                )
            )
        return PyMappingProxy(MappingProxyDict(arg)).into_pyresult_with_type(vm, class_)

    @classmethod
    def iter(cls, zelf: PyRef[PyMappingProxy], vm: VirtualMachine) -> PyObjectRef:
        return zelf._.__get_obj(vm).get_iter(vm).into_pyobject(vm)


def args_py_new(mapping: PyObjectRef, /):
    ...


@dataclass
class MappingProxyClass:
    value: PyTypeRef


@dataclass
class MappingProxyDict:
    value: PyObjectRef


MappingProxyInner = Union[MappingProxyClass, MappingProxyDict]


def init(context: PyContext) -> None:
    PyMappingProxy.extend_class(context, context.types.mappingproxy_type)
