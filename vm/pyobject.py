from __future__ import annotations

from abc import ABC, abstractclassmethod, abstractmethod, abstractstaticmethod
from dataclasses import dataclass
import dataclasses
import inspect
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ClassVar,
    Dict,
    Generic,
    Iterable,
    Iterator,
    Optional,
    Protocol,
    Type,
    TypeVar,
)


if TYPE_CHECKING:
    from vm.builtins.builtinfunc import (
        PyBuiltinFunction,
        PyBuiltinMethod,
        PyNativeFuncDef,
    )
    from vm.builtins.bytes import PyBytes
    from vm.builtins.dict import PyDict, PyDictRef
    from vm.builtins.float import PyFloat
    from vm.builtins.function import PyBoundMethod
    from vm.builtins.getset import PyGetSet, PyGetterFunc, PySetterFunc
    from vm.builtins.int import PyInt, PyIntRef
    from vm.builtins.list import PyList, PyListRef
    from vm.builtins.object import object_get_dict, object_set_dict
    from vm.builtins.pystr import PyStr, PyStrRef
    from vm.builtins.pytype import PyType, PyTypeRef
    from vm.builtins.set import PyFrozenSet
    from vm.builtins.singletons import PyNone, PyNotImplemented
    from vm.builtins.slice import PyEllipsis
    from vm.builtins.tuple import PyTuple, PyTupleRef
    from vm.exceptions import ExceptionZoo, PyBaseException
    from vm.function_ import FuncArgs, PyNativeFunc
    from vm.pyobjectrc import PyObject, PyObjectRef, PyRef
    from vm.types.slot import PyTypeFlags, PyTypeSlots
    from vm.types.zoo import TypeZoo
    from vm.vm import VirtualMachine
    from bytecode.bytecode import CodeObject
    from vm.builtins.code import PyCode
    from vm.builtins.complex import PyComplex

import vm.types.slot as slot
import vm.pyobjectrc as prc
from common.deco import (
    ImplMethodType,
    ImplSlotData,
    MethodData,
    PropertyData,
    PropertyDescriptorType,
)
from common.hash import PyHash
from common.error import PyImplBase, PyImplError, unreachable


# TODO: class attributes should maintain insertion order (use IndexMap here)
@dataclass
class PyAttributes:
    inner: dict[str, PyObjectRef] = dataclasses.field(default_factory=dict)

    def __iter__(self) -> Iterator[str]:
        return iter(self.inner.keys())

    def items(self) -> Iterable[tuple[str, PyObjectRef]]:
        return self.inner.items()

    def __getitem__(self, key: str) -> PyObjectRef:
        return self.inner[key]

    def __setitem__(self, key: str, value: PyObjectRef) -> None:
        self.inner[key] = value

    def get(self, key: str, default: T) -> T | PyObjectRef:
        return self.inner.get(key, default)

    # def insert(self, key: str, value: PyObjectRef) -> None:
    #     self.inner[key] = value

    def remove(self, key: str) -> Optional[PyObjectRef]:
        return self.inner.pop(key, None)


R = TypeVar("R")


@dataclass
class PyContext:
    true_value: PyIntRef
    false_value: PyIntRef
    none: PyRef[PyNone]
    empty_tuple: PyTupleRef
    empty_frozenset: PyRef[PyFrozenSet]
    ellipsis: PyRef[PyEllipsis]
    not_implemented: PyRef[PyNotImplemented]

    types: TypeZoo
    exceptions: ExceptionZoo
    int_cache_pool: list[PyIntRef]
    string_cache: Any  # FIXME
    slot_new_wrapper: PyObjectRef

    CONTEXT: ClassVar[Optional[PyContext]] = None

    @staticmethod
    def new() -> PyContext:
        if PyContext.CONTEXT is not None:
            return PyContext.CONTEXT
        PyContext.CONTEXT = PyContext.init()
        return PyContext.CONTEXT

    @staticmethod
    def init() -> PyContext:
        import vm.types.zoo as type_zoo
        import vm.exceptions as exception_zoo
        import vm.builtins.singletons
        import vm.builtins.slice
        import vm.builtins.int as pyint
        import vm.builtins.tuple as pytuple
        import vm.builtins.pystr as pystr
        import vm.builtins.set as pyset
        import vm.builtins.builtinfunc as builtinfunc
        import vm.builtins.pytype as pytype

        types = type_zoo.TypeZoo.init()
        exceptions = exception_zoo.ExceptionZoo.init()

        def create_object(payload: R, cls: PyTypeRef) -> PyRef[R]:
            return prc.PyRef.new_ref(payload, cls, None)

        none = create_object(
            vm.builtins.singletons.PyNone(), vm.builtins.singletons.PyNone.static_type()
        )
        ellipsis = create_object(
            vm.builtins.slice.PyEllipsis(), vm.builtins.slice.PyEllipsis.static_type()
        )
        not_implemented = create_object(
            vm.builtins.singletons.PyNotImplemented(),
            vm.builtins.singletons.PyNotImplemented.static_type(),
        )

        int_cache_pool = [
            prc.PyRef.new_ref(pyint.PyInt.from_(i), types.int_type, None)
            for i in range(INT_CACHE_POOL_MIN, INT_CACHE_POOL_MAX + 1)
        ]
        true_value = create_object(pyint.PyInt.from_(1), types.bool_type)
        false_value = create_object(pyint.PyInt.from_(0), types.bool_type)

        empty_tuple = create_object(pytuple.PyTuple([]), types.tuple_type)
        empty_frozenset = prc.PyRef.new_ref(
            pyset.PyFrozenSet.default(), types.frozenset_type, None
        )

        string_cache = {}

        new_str = prc.PyRef.new_ref(pystr.PyStr("__new__"), types.str_type, None)
        slot_new_wrapper = create_object(
            builtinfunc.PyNativeFuncDef.new(
                pytype.PyType.s__new__, new_str
            ).into_function(),
            types.builtin_function_or_method_type,
        )

        context = PyContext(
            true_value=true_value,
            false_value=false_value,
            none=none,
            empty_tuple=empty_tuple,
            empty_frozenset=empty_frozenset,
            ellipsis=ellipsis,
            not_implemented=not_implemented,
            types=types,
            exceptions=exceptions,
            int_cache_pool=int_cache_pool,
            string_cache=string_cache,
            slot_new_wrapper=slot_new_wrapper,
        )

        type_zoo.TypeZoo.extend(context)
        exception_zoo.ExceptionZoo.extend(context)

        return context

    def get_none(self) -> PyObjectRef:
        return self.none

    def get_ellipsis(self) -> PyObjectRef:
        return self.ellipsis

    def get_not_implemented(self) -> PyObjectRef:
        return self.not_implemented

    def new_method(
        self, name: PyStr, class_: PyTypeRef, f: PyNativeFunc
    ) -> PyRef[PyBuiltinMethod]:
        import vm.builtins.builtinfunc as pybuiltinfunc

        return pybuiltinfunc.PyBuiltinMethod.new_ref(name, class_, f, self)

    # TODO: move
    def new_getset(
        self, name: str, class_: PyTypeRef, g: PyGetterFunc, s: PySetterFunc
    ):
        import vm.builtins.getset as pygetset

        return prc.PyRef.new_ref(
            pygetset.PyGetSet.new(name, class_).with_get(g).with_set(s),
            self.types.getset_type,
            None,
        )

    # TODO: move
    def new_readonly_getset(self, name: str, class_: PyTypeRef, g: PyGetterFunc):
        import vm.builtins.getset as pygetset

        return prc.PyRef.new_ref(
            pygetset.PyGetSet.new(name, class_).with_get(g),
            self.types.getset_type,
            None,
        )

    # TODO: move
    def new_int(self, i: int) -> PyIntRef:
        # TODO: use self.int_cache_pool
        import vm.builtins.int as pyint

        return prc.PyRef.new_ref(pyint.PyInt(i), self.types.int_type, None)

    # TODO: move
    def new_float(self, value: float) -> PyRef[PyFloat]:
        import vm.builtins.float as pyfloat

        return prc.PyRef.new_ref(pyfloat.PyFloat(value), self.types.float_type, None)

    # TODO: move
    def new_str(self, s: str) -> PyRef[PyStr]:
        import vm.builtins.pystr as pystr

        return pystr.PyStr.from_str(s, self)

    # TODO: move
    def new_complex(self, c: complex) -> PyRef[PyComplex]:
        import vm.builtins.complex as pycomplex

        return prc.PyRef.new_ref(pycomplex.PyComplex(c), self.types.complex_type, None)

    # TODO: move
    def new_code(self, c: CodeObject) -> PyRef[PyCode]:
        import vm.builtins.code as pycode

        return prc.PyRef.new_ref(pycode.PyCode(c), self.types.code_type, None)

    # TODO: move
    def new_bytes(self, data: bytes) -> PyRef[PyBytes]:
        import vm.builtins.bytes as pybytes

        return pybytes.PyBytes.new_ref(data, self)

    def new_bool(self, b: bool) -> PyIntRef:
        return self.true_value if b else self.false_value

    # TODO: move
    def new_tuple(self, elements: list[PyObjectRef]) -> PyTupleRef:
        import vm.builtins.tuple as pytuple

        return pytuple.PyTuple.new_ref(elements, self)

    # TODO: move
    def new_list(self, elements: list[PyObjectRef]) -> PyListRef:
        import vm.builtins.list as pylist

        return pylist.PyList.new_ref(elements, self)

    # TODO: move
    def new_dict(self) -> PyDictRef:
        import vm.builtins.dict as pydict

        return pydict.PyDict.new_ref(self)

    # TODO: move
    def new_class(
        self, module: Optional[str], name: str, base: PyTypeRef, slots: PyTypeSlots
    ) -> PyTypeRef:
        import vm.builtins.pytype as pytype

        attrs = PyAttributes()
        if module is not None:
            attrs["__module__"] = self.new_str(module)
        return pytype.PyType.new_ref(name, [base], attrs, slots, self.types.type_type)

    # TODO: move
    def new_exception_type(
        self, module: str, name: str, bases: Optional[list[PyTypeRef]]
    ) -> PyTypeRef:
        import vm.builtins.pytype as pytype

        if bases is None:
            bases = [self.exceptions.exception_type]
        attrs = PyAttributes()
        attrs["__module__"] = self.new_str(module)
        return pytype.PyType.new_ref(
            name, bases, attrs, PyBaseException.make_slots(), self.types.type_type
        )

    def make_funcdef(self, name: PyStr, f: PyNativeFunc) -> PyNativeFuncDef:
        import vm.builtins.pystr as pystr
        import vm.builtins.builtinfunc as pybuiltinfunc

        return pybuiltinfunc.PyNativeFuncDef.new(f, pystr.PyStr.new_ref(name, self))

    def new_function(self, name: PyStr, f: PyNativeFunc) -> PyRef[PyBuiltinFunction]:
        return self.make_funcdef(name, f).build_function(self)


INT_CACHE_POOL_MIN = -5
INT_CACHE_POOL_MAX = 256


class TypeProtocolMixin:
    @abstractmethod
    def class_(self) -> PyTypeRef:
        ...

    # requires: class_(self) -> _
    def clone_class(self) -> PyTypeRef:
        return self.class_()

    def get_class_attr(self, attr_name: str) -> Optional[PyObjectRef]:
        return self.class_()._.get_attr(attr_name)

    def has_class_attr(self, attr_name: str) -> bool:
        return self.class_()._.has_attr(attr_name)

    def isinstance(self, cls: PyTypeRef) -> bool:
        return self.class_()._.issubclass(cls)


class PyValueMixin(ABC):
    @classmethod
    @abstractmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        ...

    def into_object(self, vm: VirtualMachine) -> PyObjectRef:
        return self.into_ref(vm)

    @staticmethod
    def special_retrieve(vm: VirtualMachine, obj: PyObject) -> Optional[PyRef]:
        return None

    def _into_ref(self, cls: PyTypeRef, vm: VirtualMachine) -> PyRef:
        if cls._.slots.flags.has_feature(slot.PyTypeFlags.HAS_DICT):
            dict_ = vm.ctx.new_dict()
        else:
            dict_ = None
        return prc.PyRef.new_ref(self, cls, dict_)

    def into_ref(self, vm: VirtualMachine) -> PyRef:
        cls = self.__class__.class_(vm)
        return self._into_ref(cls, vm)

    def into_ref_with_type(self, vm: VirtualMachine, cls: PyTypeRef) -> PyRef:
        exact_class = self.__class__.class_(vm)
        if cls._.issubclass(exact_class):
            return self._into_ref(cls, vm)
        else:
            vm.new_type_error(
                f"'{cls._.name()}'is not a subtype of '{exact_class._.name()}'"
            )

    def into_pyresult_with_type(
        self, vm: VirtualMachine, cls: PyTypeRef
    ) -> PyObjectRef:
        return self.into_ref_with_type(vm, cls)


@dataclass
class PyClassDef:
    NAME: ClassVar[str]
    MODULE_NAME: ClassVar[Optional[str]]
    TP_NAME: ClassVar[str]
    DOC: ClassVar[Optional[str]]


class _PyClassProtocol(Protocol):
    NAME: str
    TP_NAME: str
    MODULE_NAME: Optional[str]
    DOC: Optional[str]


PC = TypeVar("PC", bound=_PyClassProtocol)


# class ICProtocol(_PyClassProtocol):
#     NAME: str
#     TP_NAME: str
#     MODULE_NAME: Optional[str]
#     DOC: Optional[str]
#     pyimpl_at: __PyImplData


@dataclass
class ImplProperty:
    name: str
    getter: Optional[MethodData] = None
    setter: Optional[MethodData] = None
    deleter: Optional[MethodData] = None


IC = TypeVar("IC")


def pyimpl(
    *,
    py_ref: Optional[bool] = None,
    view_set_opts: Optional[bool] = None,
    dict_view: Optional[bool] = None,
    iter_next: Optional[bool] = None,
    iterable: Optional[bool] = None,
    callable: Optional[bool] = None,
    as_mapping: Optional[bool] = None,
    as_sequence: Optional[bool] = None,
    as_buffer: Optional[bool] = None,
    hashable: Optional[bool] = None,
    comparable: Optional[bool] = None,
    get_descriptor: Optional[bool] = None,
    constructor: Optional[bool] = None,
    get_attr: Optional[bool] = None,
    set_attr: Optional[bool] = None,
) -> Callable[[IC], IC]:
    def inner(cls: IC) -> IC:
        impl = cls.pyimpl_at  # type: ignore
        if impl is None:
            impl = cls.pyimpl_at = PyClassImplData()  # type: ignore
        # assert isinstance(impl, PyClassImplData)
        ms = [
            (mem, getattr(mem, "pyimpl_at"))
            for _, mem in inspect.getmembers(cls)
            if hasattr(mem, "pyimpl_at")
        ]

        for mem, data in ms:
            if isinstance(data, MethodData):
                data.method = mem
                impl.methods[data.name] = data
            elif isinstance(data, PropertyData):
                data.method_data.method = mem
                if data.name not in impl.properties:
                    impl.properties[data.name] = ImplProperty(data.name)
                prop = impl.properties[data.name]
                if data.descriptor_type == PropertyDescriptorType.GETTER:
                    assert prop.getter is None, prop
                    prop.getter = data.method_data
                elif data.descriptor_type == PropertyDescriptorType.SETTER:
                    assert prop.setter is None, prop
                    prop.setter = data.method_data
                elif data.descriptor_type == PropertyDescriptorType.DELETER:
                    assert prop.deleter is None, prop
                    prop.deleter = data.method_data
                else:
                    assert False, data.descriptor_type
            elif isinstance(data, ImplSlotData):
                data.method_data.method = mem
                method = data.method_data.method
                # sig = inspect.signature(method)
                # TODO!!! check that the signatures match
                if data.name == "as_sequence":
                    assert impl.slots.as_sequence is None
                    impl.slots.as_sequence = method
                elif data.name == "as_mapping":
                    assert impl.slots.as_mapping is None
                    impl.slots.as_mapping = method
                elif data.name == "hash":
                    assert impl.slots.hash is None
                    impl.slots.hash = method
                elif data.name == "call":
                    assert impl.slots.call is None
                    impl.slots.call = method
                elif data.name == "getattro":
                    assert impl.slots.getattro is None
                    impl.slots.getattro = method
                elif data.name == "setattro":
                    assert impl.slots.setattro is None
                    impl.slots.setattro = method
                elif data.name == "as_buffer":
                    assert impl.slots.as_buffer is None
                    impl.slots.as_buffer = method
                elif data.name == "richcompare":
                    assert impl.slots.richcompare is None
                    impl.slots.richcompare = method
                elif data.name == "iter":
                    assert impl.slots.iter is None
                    impl.slots.iter = method
                elif data.name == "iternext":
                    assert impl.slots.iternext is None
                    impl.slots.iternext = method
                elif data.name == "descr_get":
                    assert impl.slots.descr_get is None
                    impl.slots.descr_get = method
                elif data.name == "descr_set":
                    assert impl.slots.descr_set is None
                    impl.slots.descr_set = method
                elif data.name == "new":
                    assert impl.slots.new is None
                    impl.slots.new = method
                elif data.name == "del":
                    assert impl.slots.del_ is None
                    impl.slots.del_ = method
                else:
                    assert False, data.name

            else:
                assert False, data
        return cls

    return inner


# TODO: use `base`
def pyexception(name: str, base: str, doc: str):
    def inner(cls):
        cls.NAME = name
        cls.TP_NAME = name
        cls.MODULE_NAME = None
        cls.DOC = doc
        return cls

    return inner


# TODO: use `base`
def pyclass(
    name: str,
    *,
    tp_name: Optional[str] = None,
    module_name: Optional[str] = None,
    doc: Optional[str] = None,
    base: Optional[str] = None,
) -> Callable[[PC], PC]:
    if tp_name is None:
        tp_name = name  # FIXME?

    def inner(cls: PC) -> PC:
        cls.NAME = name
        cls.TP_NAME = tp_name
        cls.MODULE_NAME = module_name
        cls.DOC = doc

        return cls

    return inner


@dataclass
class StaticTypeMixin:
    STATIC_CELL: ClassVar[Optional[PyTypeRef]] = None

    @classmethod
    def static_cell(cls) -> Optional[PyTypeRef]:
        return cls.STATIC_CELL

    @classmethod
    def set_static_cell(cls, type: PyTypeRef) -> None:
        cls.STATIC_CELL = type

    @classmethod
    def static_metaclass(cls) -> PyTypeRef:
        import vm.builtins.pytype as pytype

        return pytype.PyType.static_type()

    @classmethod
    def static_baseclass(cls) -> PyTypeRef:
        import vm.builtins.object as oo

        return oo.PyBaseObject.static_type()

    @classmethod
    def static_type(cls) -> PyTypeRef:
        r = cls.static_cell()
        assert r is not None, "static type has not been initialized"
        return r

    @classmethod
    def init_manually(cls, type: PyTypeRef) -> PyTypeRef:
        cell = cls.static_cell()
        assert cell is None, "double initialization from init_manually"
        cls.set_static_cell(type)
        return type

    @classmethod
    def init_bare_type(cls) -> PyTypeRef:
        # requires: `cls: PyClassImpl`
        type = cls.create_bare_type()
        cell = cls.static_cell()
        assert cell is None, f"double initialization of {cls.NAME}"  # type: ignore
        cls.set_static_cell(type)
        return type

    @classmethod
    def create_bare_type(cls) -> PyTypeRef:
        import vm.builtins.pytype as pytype

        # requires: `cls: PyClassImpl`
        return pytype.PyType.new_ref(
            cls.NAME,  # type: ignore
            [cls.static_baseclass()],
            PyAttributes(),
            cls.make_slots(),  # type: ignore
            cls.static_metaclass(),
        )


class TPProtocol(Protocol):
    TP_FLAGS: PyTypeFlags


TP = TypeVar("TP", bound=TPProtocol)


def tp_flags(
    *, basetype=False, has_dict=False, method_descr=False, heaptype=False
) -> Callable[[TP], TP]:
    def inner(cls: TP) -> TP:
        flags = slot.PyTypeFlags.default()
        if basetype:
            flags |= slot.PyTypeFlags.BASETYPE
        if has_dict:
            flags |= slot.PyTypeFlags.HAS_DICT
        if method_descr:
            flags |= slot.PyTypeFlags.METHOD_DESCR
        if heaptype:
            flags |= slot.PyTypeFlags.HEAPTYPE
        cls.TP_FLAGS = flags
        return cls

    return inner


@dataclass
class PyClassImplData:
    methods: dict[str, MethodData] = dataclasses.field(default_factory=dict)
    properties: dict[str, ImplProperty] = dataclasses.field(default_factory=dict)
    slots: PyTypeSlots = dataclasses.field(default_factory=slot.PyTypeSlots.default)


def make_getter(getter: MethodData) -> PyGetterFunc:
    def foo(vm: VirtualMachine, obj: PyObjectRef) -> PyObjectRef:
        # TODO: catch & handle exceptions
        return getter.method(obj._, vm=vm)
        # return res.into_ref(vm)

    return foo


def make_setter(setter: MethodData) -> PySetterFunc:
    def foo(vm: VirtualMachine, obj: PyObjectRef, value: PyObjectRef) -> None:
        # TODO: catch & handle exceptions
        setter.method(obj, value, vm=vm)  # FIXME?
        # return res.into_ref(vm)  # FIXME? check that it doesnt return a value?

    return foo


def make_method(method: MethodData) -> PyNativeFunc:
    sig = inspect.signature(method.method)

    get_self_arg = None
    if method.type == ImplMethodType.INSTANCE:
        first_arg = list(sig.parameters)[0]
        if first_arg == "self":
            get_self_arg = lambda x: x._
        elif first_arg == "zelf":
            get_self_arg = lambda x: x
        else:
            unreachable(
                f"first arg is '{first_arg}' in method '{method.name}' [{method.method}]"
            )

    def func(vm: VirtualMachine, fargs: FuncArgs) -> PyObjectRef:
        # TODO: catch & handle exceptions
        assert "vm" not in fargs.kwargs
        bs = sig.bind(*fargs.args, **fargs.kwargs, vm=vm)

        res = method.method(
            *([get_self_arg(fargs.args[0])] if get_self_arg is not None else []),
            *[
                method.casts[n](vm, v) if method.casts is not None else v
                for n, v in list(zip(bs.arguments, fargs.args))[bool(get_self_arg) :]
            ],
            **{
                k: method.casts[k](vm, v) if method.casts is not None else v
                for k, v in fargs.kwargs.items()
            },
            vm=vm,
        )
        if isinstance(res, prc.PyRef):
            return res
        # TODO? move to decorator?
        elif isinstance(res, PyValueMixin):
            return res.into_ref(vm)
        else:
            return primitive_to_pyobject(res, vm)

    return func


def primitive_to_pyobject(
    value: bool
    | int
    | float
    | complex
    | str
    | bytes
    | PyArithmeticValue[bool | int | float | complex | str | bytes]
    | None,
    vm: VirtualMachine,
) -> PyObjectRef:
    if value is None:
        return vm.ctx.get_none()
    elif isinstance(value, bool):
        return vm.ctx.new_bool(value)
    elif isinstance(value, int):
        return vm.ctx.new_int(value)
    elif isinstance(value, float):
        return vm.ctx.new_float(value)
    elif isinstance(value, complex):
        return vm.ctx.new_complex(value)
    elif isinstance(value, str):
        return vm.ctx.new_str(value)
    elif isinstance(value, bytes):
        return vm.ctx.new_bytes(value)
    elif isinstance(value, PyArithmeticValue):
        if value.value is not None:
            if isinstance(value.value, prc.PyRef):
                return value.value
            else:
                return primitive_to_pyobject(value.value, vm)
        else:
            return vm.ctx.get_not_implemented()
    else:
        assert False, type(value)


class PyModuleImpl:
    @classmethod
    def extend_module(cls, vm: VirtualMachine, module: PyObject) -> None:
        pyfunctions = getattr(cls, "pyfunctions", None)
        assert pyfunctions is not None
        assert isinstance(pyfunctions, dict)
        for name, func in pyfunctions.items():
            assert isinstance(name, str)
            new_func = (
                vm.ctx.make_funcdef(vm.mk_str(name)._, func)
                .with_doc("TODO", vm.ctx)  # TODO!
                .into_function()
                .with_module(vm.new_pyobj(module))
                .into_ref(vm.ctx)
            )
            vm.module_set_attr(module, vm.mk_str(name), new_func)
        # TODO: impl other kinds of module attributes

    @classmethod
    def make_module(cls, vm: VirtualMachine) -> PyObjectRef:
        module = vm.new_module(cls.__name__, vm.ctx.new_dict(), cls.__doc__)
        cls.extend_module(vm, module)
        return module


class TryFromObjectRequirements(Protocol):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        ...

    @classmethod
    def special_retrieve(
        cls: Type[T], vm: VirtualMachine, obj: PyObjectRef
    ) -> PyRef[T]:
        ...

    @classmethod
    def try_from_object(cls: Type[T], vm: VirtualMachine, obj: PyObjectRef) -> T:
        ...


TT = TypeVar("TT", bound=TryFromObjectRequirements)


class TryFromObjectMixin:
    @classmethod
    def try_from_object(cls: Type[TT], vm: VirtualMachine, obj: PyObjectRef) -> TT:
        class_ = cls.class_(vm)
        if obj.isinstance(class_):
            try:
                return obj.downcast(cls)._
            except PyImplError as e:
                prc.pyref_payload_error(vm, class_, e.obj)
        else:
            try:
                return cls.special_retrieve(vm, obj)._
            except PyImplBase as _:
                prc.pyref_type_error(vm, class_, obj)


@dataclass
class PyClassImpl(PyClassDef, StaticTypeMixin, PyValueMixin, TryFromObjectMixin):
    TP_FLAGS: ClassVar[PyTypeFlags] = slot.PyTypeFlags.default()
    pyimpl_at: ClassVar[PyClassImplData] = None  # type: ignore

    @classmethod
    def impl_extend_class(cls, ctx: PyContext, class_: PyTypeRef) -> None:
        for method in cls.pyimpl_at.methods.values():
            # if method.type == ImplMethodType.INSTANCE:
            func = make_method(method)
            new_method = ctx.new_method(ctx.new_str(method.name)._, class_, func)
            class_._.set_str_attr(method.name, new_method)
            # elif method.type == ImplMethodType.CLASS:
            #     func = make_method(method)

        for prop in cls.pyimpl_at.properties.values():
            assert prop.deleter is None, prop
            if prop.getter is not None:
                getter = make_getter(prop.getter)
                if prop.setter is None:
                    getset = ctx.new_readonly_getset(prop.name, class_, getter)
                elif prop.setter is not None:
                    setter = make_setter(prop.setter)
                    getset = ctx.new_getset(prop.name, class_, getter, setter)
                else:
                    assert False, prop
            else:
                assert False, prop
            # FIXME?
            class_._.set_str_attr(prop.name, getset)

    @classmethod
    def extend_class(cls, ctx: PyContext, class_: PyTypeRef) -> None:
        import vm.builtins.function as pyfunction

        if cls.TP_FLAGS.has_feature(slot.PyTypeFlags.HAS_DICT):
            class_._.set_str_attr(
                "__dict__",
                ctx.new_getset(
                    "__dict__",
                    class_,
                    lambda vm, obj: object_get_dict(obj, vm),
                    lambda vm, obj, value: object_set_dict(obj, value, vm),
                ),
            )
        cls.impl_extend_class(ctx, class_)
        if cls.DOC is not None:
            class_._.set_str_attr("__doc__", ctx.new_str(cls.DOC))
        if cls.MODULE_NAME is not None:
            class_._.set_str_attr("__module__", ctx.new_str(cls.MODULE_NAME))
        if class_._.slots.new is not None:
            bound = pyfunction.PyBoundMethod.new_ref(class_, ctx.slot_new_wrapper, ctx)
            class_._.set_str_attr("__new__", bound)

    @classmethod
    def make_class(cls, ctx: PyContext) -> PyTypeRef:
        cell = cls.static_cell()
        if cell is None:
            cell = cls.create_bare_type()
            cls.extend_class(ctx, cell)
            cls.set_static_cell(cell)
        return cell

    # unused
    # @classmethod
    # def extend_slots(cls, slots: PyTypeSlots) -> None:

    @classmethod
    def make_slots(cls) -> PyTypeSlots:
        return cls.pyimpl_at.slots.with_(
            flags=cls.TP_FLAGS, name=cls.TP_NAME, doc=cls.DOC
        )


T = TypeVar("T")


@dataclass
class PyArithmeticValue(Generic[T]):
    value: Optional[T]

    @staticmethod
    def from_object(
        vm: VirtualMachine, obj: PyObjectRef
    ) -> PyArithmeticValue[PyObjectRef]:
        if obj.is_(vm.ctx.not_implemented):
            return PyArithmeticValue(None)
        else:
            return PyArithmeticValue(obj)

    def is_implemented(self) -> bool:
        return self.value is not None

    # def unwrap_or_unimplemented(self, vm: VirtualMachine) -> PyObjectRef | T:

    def into_pyobject(self, vm: VirtualMachine) -> PyObjectRef:
        if self.value is None:
            return vm.ctx.get_not_implemented()
        assert isinstance(self.value, PyValueMixin)
        return self.value.into_ref(vm)


PyComparisonValue = PyArithmeticValue[bool]


@dataclass
class PySequenceL(Generic[T]):
    value: list[T]

    def into_vec(self) -> list[T]:
        return self.value

    def as_slice(self) -> list[T]:
        return self.value

    @classmethod
    def try_from_object(
        cls, vm: VirtualMachine, obj: PyObjectRef
    ) -> PySequenceL[PyObjectRef]:
        return PySequenceL(vm.extract_elements_as_pyobjects(obj))


@dataclass
class PyMethod(ABC):
    @staticmethod
    def get(obj: PyObjectRef, name: PyStrRef, vm: VirtualMachine) -> PyMethod:
        cls = obj.class_()
        getattro = cls._.mro_find_map(lambda cls: cls.slots.getattro)
        assert getattro is not None, cls._.name()
        # TODO:
        # if getattro as usize != object::PyBaseObject::getattro as usize {
        #     drop(cls);
        #     return obj.get_attr(name, vm).map(Self::Attribute);
        # }
        is_method = False
        if (descr := cls._.get_attr(name._.as_str())) is not None:
            descr_cls = descr.class_()
            if slot.PyTypeFlags.METHOD_DESCR in descr_cls._.slots.flags:
                is_method = True
                descr_get = None
            else:
                descr_get = descr_cls._.mro_find_map(lambda cls: cls.slots.descr_get)
                if descr_get is not None:
                    if (
                        descr_cls._.mro_find_map(lambda cls: cls.slots.descr_set)
                        is not None
                    ):
                        return PyMethodAttribute(
                            descr_get(descr, obj, cls.into_pyobj(vm), vm)
                        )
            cls_attr = (descr, descr_get)
        else:
            cls_attr = None

        if (
            obj.dict is not None
            and (attr := obj.dict.get_item_opt(name, vm)) is not None
        ):
            return PyMethodAttribute(attr)

        if cls_attr is not None:
            attr, descr_get = cls_attr
            if descr_get is None and is_method:
                return PyMethodFunction(target=obj, func=attr)
            elif descr_get is not None:
                return PyMethodAttribute(descr_get(attr, obj, cls.into_pyobj(vm), vm))
            else:
                return PyMethodAttribute(attr)
        elif (getter := cls.get_attr(vm.mk_str("__getattr__"), vm)) is not None:
            return PyMethodAttribute(vm.invoke(getter, FuncArgs([obj, name])))
        else:
            vm.new_attribute_error(f"'{cls._.name()}' object has no attribute '{name}'")
            # TODO: vm.set_attribute_error_context(&exc, obj.clone(), name);

    @staticmethod
    def get_special(obj: PyObjectRef, name: str, vm: VirtualMachine) -> PyMethod:
        obj_cls = obj.class_()
        func = obj_cls._.get_attr(name)
        if func is None:
            raise PyImplError(obj)
        if func.class_()._.slots.flags.has_feature(slot.PyTypeFlags.METHOD_DESCR):
            return PyMethodFunction(target=obj, func=func)
        else:
            attr = vm.call_get_descriptor_specific(func, obj, obj_cls)
            return PyMethodAttribute(attr)

    @abstractmethod
    def invoke(self, args: FuncArgs, vm: VirtualMachine) -> PyObjectRef:
        ...

    def invoke_ref(self, args: FuncArgs, vm: VirtualMachine) -> PyObjectRef:
        return self.invoke(args, vm)


@dataclass
class PyMethodFunction(PyMethod):
    target: PyObjectRef
    func: PyObjectRef

    def invoke(self, args: FuncArgs, vm: VirtualMachine) -> PyObjectRef:
        return vm.invoke(self.func, args.into_method_args(self.target, vm))


@dataclass
class PyMethodAttribute(PyMethod):
    func: PyObjectRef

    def invoke(self, args: FuncArgs, vm: VirtualMachine) -> PyObjectRef:
        return vm.invoke(self.func, args.into_args(vm))


@tp_flags(basetype=True)
@pyimpl(callable=True, hashable=True, comparable=True, constructor=True)
@pyclass("weakref")
@dataclass
class PyWeak(PyClassImpl, PyValueMixin):
    # TODO
    pointers: Any
    parent: Any
    callback: Optional[PyObjectRef]
    hash: PyHash

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.weakref_type


@dataclass
class PyObjectWeak:
    weak: PyRef[PyWeak]
