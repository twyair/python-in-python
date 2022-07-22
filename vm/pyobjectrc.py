from __future__ import annotations
from collections import OrderedDict
from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Generic,
    NoReturn,
    Optional,
    Protocol,
    Type,
    TypeVar,
    final,
)
from common import to_opt
from common.error import PyImplBase, PyImplError, PyImplException
from common.hash import PyHash

if TYPE_CHECKING:
    from vm.builtins.genericalias import PyGenericAlias
    from vm.builtins.pytype import PyTypeRef
    from vm.builtins.dict import PyDict, PyDictRef
    from vm.builtins.pystr import PyStrRef
    from vm.builtins.tuple import PyTuple
    from vm.function_ import FuncArgs
    from vm.protocol.iter import PyIter
    from vm.protocol.mapping import PyMapping
    from vm.pyobject import PyArithmeticValue, PyObjectWeak
    from vm.types.slot import PyComparisonOp, PyTypeFlags
    from vm.vm import VirtualMachine
    from vm.protocol.sequence import PySequence

import vm.function_ as fn

T = TypeVar("T")


def bool_get_value(obj: PyObject) -> bool:
    import vm.builtins.int as pyint

    p = obj.payload_(pyint.PyInt)
    assert p is not None
    return p.value != 0


@dataclass
class InstanceDict:
    d: PyDictRef

    def set(self, d: PyDictRef) -> None:
        self.d = d

    def set_item(self, k: PyStrRef, v: PyObjectRef, vm: VirtualMachine) -> None:
        self.d._.set_item(k, v, vm)

    def del_item(self, k: PyStrRef, vm: VirtualMachine) -> None:
        self.d._.del_item(k, vm)

    # FIXME: should raise an exception when item is `None`
    def get_item(self, k: PyStrRef, vm: VirtualMachine) -> Optional[PyObjectRef]:
        return self.d._.get_item_opt(k, vm)

    def get_item_opt(self, k: PyStrRef, vm: VirtualMachine) -> Optional[PyObjectRef]:
        return self.d._.get_item_opt(k, vm)


R = TypeVar("R")


PyRefT = TypeVar("PyRefT")


@final
@dataclass
class PyRef(Generic[PyRefT]):
    type: PyTypeRef
    dict: Optional[InstanceDict]
    payload: PyRefT

    def debug_repr(self) -> str:
        payload_repr = getattr(self._, "debug_repr", lambda: "...")()
        return "<'{}' @ '{}' : '{}'>".format(
            payload_repr, self._.__class__.__name__, self.type._.name()
        )

    @property
    def _(self) -> PyRefT:
        return self.payload

    @staticmethod
    def new_ref(
        payload: PyRefT, type: PyTypeRef, dict: Optional[PyDictRef]
    ) -> PyRef[PyRefT]:
        return PyRef[PyRefT](
            type=type,
            dict=InstanceDict(dict) if dict is not None else None,
            payload=payload,
        )

    def into_pyobj(self, vm: VirtualMachine) -> PyObjectRef:
        return self  # ._.into_ref(vm)

    def has_attr(self, attr_name: PyStrRef, vm: VirtualMachine) -> bool:
        return vm.is_none(self.get_attr(attr_name, vm))

    def get_attr(self, attr_name: PyStrRef, vm: VirtualMachine) -> PyObjectRef:
        getattro = self.class_()._.mro_find_map(lambda cls: cls.slots.getattro)
        # print("getattro", getattro)
        assert getattro is not None, (
            self.class_()._.name(),
            [c._.name() for c in self.class_()._.mro_],
            [c._.slots.getattro is None for c in self.class_()._.mro_],
        )
        return getattro(self, attr_name, vm)

    def set_dict(self, dict: PyDictRef) -> None:
        if self.dict is None:
            raise PyImplError(dict)
        self.dict.set(dict)

    def downgrade_with_type(
        self, callback: Optional[PyObjectRef], type: PyTypeRef, vm: VirtualMachine
    ) -> PyObjectWeak:
        dic = None
        if type._.slots.flags.has_feature(PyTypeFlags.HAS_DICT):
            dict_ = vm.ctx.new_dict()
        cls_is_weakref = type.is_(vm.ctx.types.weakref_type)
        raise NotImplementedError

    def downgrade(self, callback: Optional[PyObjectRef], vm: VirtualMachine):
        return self.downgrade_with_type(callback, vm.ctx.types.weakref_type, vm)

    # def weak_ref_list(self) -> Optional[WeakRefList]:
    #     return self

    # def downgrade_with_weakref_typ_opt(self, callback: Optional[PyObjectRef], typ: PyTypeRef) -> Optional[PyObjectWeak]:
    #     r = self.weak_ref_list()
    #     if r is None:
    #         return None

    def payload_if_subclass(self, t: Type[PT], vm: VirtualMachine) -> Optional[PT]:
        if self.class_()._.issubclass(t.class_(vm)):
            return self.payload_(t)
        else:
            return None

    def payload_is(self, t: Type[PT]) -> bool:
        # TODO: is that correct?
        return isinstance(self._, t)

    def call_set_attr(
        self, vm: VirtualMachine, attr_name: PyStrRef, attr_value: Optional[PyObjectRef]
    ) -> None:
        cls = self.class_()
        setattro = cls._.mro_find_map(lambda cls: cls.slots.setattro)
        if setattro is None:
            assign = attr_value is not None
            has_getattr = cls._.mro_find_map(lambda cls: cls.slots.getattro) is not None
            vm.new_type_error(
                "'{}' object has {} attributes ({} {})".format(
                    cls._.name(),
                    "only read-only" if has_getattr else "no",
                    "assign to" if assign else "del",
                    attr_name,
                )
            )
        setattro(self, attr_name, attr_value, vm)

    def set_attr(
        self, attr_name: PyStrRef, attr_value: PyObjectRef, vm: VirtualMachine
    ) -> None:
        self.call_set_attr(vm, attr_name, attr_value)

    def del_attr(self, attr_name: PyStrRef, vm: VirtualMachine) -> None:
        self.call_set_attr(vm, attr_name, None)

    def _cmp(
        self, other: PyObject, op: PyComparisonOp, vm: VirtualMachine
    ) -> PyObjectRef | bool:
        swapped = op.swapped()

        def call_cmp(
            obj: PyObject, other: PyObject, op: PyComparisonOp
        ) -> PyArithmeticValue[bool] | PyArithmeticValue[PyObjectRef]:
            import vm.pyobject as po

            cmp = obj.class_()._.mro_find_map(lambda cls: cls.slots.richcompare)
            assert cmp is not None
            r = cmp(obj, other, op, vm)
            if isinstance(r, PyRef):
                return po.PyArithmeticValue.from_object(vm, r)
            else:
                return r

        checked_reverse_op = False
        self_class = self.class_()
        other_class = other.class_()
        is_strict_subclass = not self_class.is_(
            other_class
        ) and other_class._.issubclass(self_class)
        if is_strict_subclass:
            x = vm.with_recursion(
                "in comparison", lambda: call_cmp(other, self, swapped)
            )
            checked_reverse_op = True
            if x.value is not None:
                return x.value
        x = vm.with_recursion("in comparison", lambda: call_cmp(self, other, op))
        if x.value is not None:
            return x.value
        if not checked_reverse_op:
            x = vm.with_recursion(
                "in comparison", lambda: call_cmp(other, self, swapped)
            )
            checked_reverse_op = True
            if x.value is not None:
                return x.value
        if op == PyComparisonOp.Eq:
            return self.is_(other)
        elif op == PyComparisonOp.Ne:
            return not self.is_(other)
        else:
            vm.new_unsupported_binop_error(self, other, op.operator_token())

    def rich_compare(
        self, other: PyObjectRef, opid: PyComparisonOp, vm: VirtualMachine
    ) -> PyObjectRef:
        res = self._cmp(other, opid, vm)
        if isinstance(res, PyRef):
            return res
        return vm.ctx.new_bool(res)

    def rich_compare_bool(
        self, other: PyObject, opid: PyComparisonOp, vm: VirtualMachine
    ) -> bool:
        obj = self._cmp(other, opid, vm)
        if isinstance(obj, bool):
            return obj
        return obj.try_to_bool(vm)

    def repr(self, vm: VirtualMachine) -> PyStrRef:
        import vm.builtins.pystr as pystr

        return vm.with_recursion(
            "while getting the repr of an object",
            lambda: pystr.PyStr.try_from_object(
                vm,
                vm.call_special_method(self, "__repr__", fn.FuncArgs()),
            ),
        )

    def ascii(self, vm: VirtualMachine) -> AsciiString:
        raise NotImplementedError

    def str(self, vm: VirtualMachine) -> PyStrRef:
        import vm.builtins.pystr as pystr

        if self.class_().is_(vm.ctx.types.str_type):
            return self.downcast(pystr.PyStr)
        else:
            return pystr.PyStr.try_from_object(
                vm, vm.call_special_method(self, "__str__", fn.FuncArgs())
            )

    # TODO?
    # def try_into_value(self, t: Type[PT], vm: VirtualMachine) -> PyRef[PT]:

    def check_cls(
        self, cls: PyObject, vm: VirtualMachine, msg: Callable[[], str]
    ) -> PyObjectRef:
        try:
            return cls.get_attr(vm.mk_str("__bases__"), vm)
        except PyImplException as e:
            if e.exception.class_().is_(vm.ctx.exceptions.attribute_error):
                vm.new_type_error(msg())
            raise

    def abstract_issubclass(self, cls: PyObject, vm: VirtualMachine) -> bool:
        derived = self
        first_item = None
        while 1:
            if derived.is_(cls):
                return True

            bases = derived.get_attr(vm.mk_str("__bases__"), vm)
            tuple = PyTuple.try_from_object(vm, bases)
            n = tuple._.len()
            if n == 0:
                return False
            elif n == 1:
                first_item = tuple._.fast_getitem(0)
                derived = first_item
                continue
            else:
                for i in range(n):
                    try:
                        r = tuple._.fast_getitem(i).abstract_issubclass(cls, vm)
                    except PyImplBase:
                        pass
                    else:
                        if r:
                            return True
            break
        return False

    def clone(self) -> PyObjectRef:
        return self  # FIXME?

    @staticmethod
    def from_obj_unchecked(obj: PyObjectRef) -> PyRef[PyRefT]:
        return obj

    def dict_(self) -> Optional[PyDictRef]:
        if self.dict is None:
            return None
        else:
            return self.dict.d

    def downcast(self, t: Type[PT]) -> PyRef[PT]:
        if self.payload_is(t):
            return PyRef[PT].from_obj_unchecked(self)
        else:
            raise PyImplError(self)

    def downcast_ref(self, t: Type[PT]) -> Optional[PyRef[PT]]:
        if self.payload_is(t):
            return self.downcast_unchecked_ref(t)
        else:
            return None

    def downcast_ref_if_exact(
        self, t: Type[PT], vm: VirtualMachine
    ) -> Optional[PyRef[PT]]:
        if self.class_().is_(t.class_(vm)):
            return self.downcast_unchecked_ref(t)
        return None

    def downcast_unchecked(self, t: Type[PT]) -> PyRef[PT]:
        assert self.payload_is(t), (self, t)
        return self  # type: ignore

    def downcast_unchecked_ref(self, t: Type[PT]) -> PyRef[PT]:
        assert self.payload_is(t), self
        return self  # type: ignore

    def downcast_exact(self, t: Type[PT], vm: VirtualMachine) -> PyRef[PT]:
        if self.class_().is_(t.class_(vm)):
            assert self.payload_is(t), "obj.__clas__ is T::class() but payload is not T"
            return PyRef[PT].from_obj_unchecked(self)
        else:
            raise PyImplError(self)

    def as_object(self) -> PyObject:
        return self

    def class_(self, vm: VirtualMachine = ...) -> PyTypeRef:
        return self.type

    def clone_class(self) -> PyTypeRef:
        # FIXME?
        return self.type

    def get_class_attr(self, attr_name: str) -> Optional[PyObjectRef]:
        return self.class_()._.get_attr(attr_name)

    def has_class_attr(self, attr_name: str) -> bool:
        return self.class_()._.has_attr(attr_name)

    def isinstance(self, cls: PyTypeRef) -> bool:
        return self.class_()._.issubclass(cls)

    def is_instance(self, cls: PyObject, vm: VirtualMachine) -> bool:
        import vm.builtins.tuple as pytuple

        if self.class_().is_(cls):
            return True
        if cls.class_().is_(vm.ctx.types.type_type):
            return self.abstract_isinstance(cls, vm)
        if (tuple := pytuple.PyTuple.try_from_object(vm, cls)) is not None:
            for type in tuple._.as_slice():
                if vm.with_recursion(
                    "in __instancecheck__", lambda: self.is_instance(type, vm)
                ):
                    return True
            return False

        if (meth := vm.get_special_method(cls, "__instancecheck__")) is not None:
            ret = vm.with_recursion(
                "in __instancecheck__",
                lambda: meth.invoke(fn.FuncArgs([self]), vm),
            )
            return ret.try_to_bool(vm)

        return self.abstract_isinstance(cls, vm)

    def recursive_issubclass(self, cls: PyObject, vm: VirtualMachine) -> bool:
        raise NotImplementedError

    def is_subclass(self, cls: PyObject, vm: VirtualMachine) -> bool:
        if cls.class_().is_(vm.ctx.types.type_type):
            if self.is_(cls):
                return True
            else:
                return self.recursive_issubclass(cls, vm)
        raise NotImplementedError

    def abstract_isinstance(self, cls: PyObject, vm: VirtualMachine) -> bool:
        import vm.builtins.pytype as pytype

        if (type := to_opt(lambda: pytype.PyType.try_from_object(vm, cls))) is not None:
            if self.class_()._.issubclass(type):
                return True
            elif icls := pytype.PyType.try_from_object(
                vm, self.get_attr(vm.mk_str("__class__"), vm)
            ):
                if icls.is_(self.class_()):
                    return False
                else:
                    return icls._.issubclass(type)
            else:
                return False
        else:
            self.check_cls(
                cls,
                vm,
                lambda: f"isinstance() arg 2 must be a type or tuple of types, not {cls.class_()}",
            )
            icls = self.get_attr(vm.mk_str("__class__"), vm)
            if vm.is_none(icls):
                return False
            else:
                return icls.abstract_issubclass(cls, vm)

    def try_into_value(self, t: Type[PT], vm: VirtualMachine) -> PT:
        return t.try_from_object(vm, self)._

    def try_bytes_like(self, vm: VirtualMachine, f: Callable[[bytes], R]) -> R:
        import vm.protocol.buffer as buffer

        buff = buffer.PyBuffer.try_from_borrowed_object(vm, self)
        if (x := buff.as_contiguous()) is not None:
            return f(x)
        else:
            vm.new_type_error("non-contiguous buffer is not a bytes-like object")

    def try_to_float(self, vm: VirtualMachine) -> Optional[float]:
        import vm.builtins.int as pyint
        import vm.builtins.float as pyfloat

        if (f := self.payload_if_exact(pyfloat.PyFloat, vm)) is not None:
            return f.value
        if (method := vm.get_method(self, "__float__")) is not None:
            result = vm.invoke(method, FuncArgs())
            if (float_obj := result.payload_(pyfloat.PyFloat)) is not None:
                return float_obj.value
            else:
                vm.new_type_error(
                    f"__float__ returned non-float (type '{result.class_()._.name()}')"
                )
        if (r := vm.to_index_opt(self)) is not None:
            return pyint.try_bigint_to_f64(r._.as_int(), vm)
        return None

    def try_to_bool(self, vm: VirtualMachine) -> bool:
        import vm.builtins.int as pyint

        if self.is_(vm.ctx.true_value):
            return True
        if self.is_(vm.ctx.false_value):
            return False
        if (method := vm.get_method(self, "__bool__")) is not None:
            bool_obj = vm.invoke(method, fn.FuncArgs([], OrderedDict()))
            if not bool_obj.isinstance(vm.ctx.types.bool_type):
                vm.new_type_error(
                    f"__bool__ should return bool, returned type {bool_obj.class_()._.name()}"
                )
            return bool_get_value(bool_obj)
        else:
            if (method := vm.get_method(self, "__len__")) is not None:
                bool_obj = vm.invoke(method, fn.FuncArgs([], OrderedDict()))
                int_obj = bool_obj.downcast_exact(pyint.PyInt, vm)._
                len_val = int_obj.value
                if len_val < 0:
                    vm.new_value_error("__len__() should return >= 0")
                return len_val != 0
            else:
                return True

    def length_opt(self, vm: VirtualMachine) -> Optional[int]:
        from vm.protocol.sequence import PySequence  # FIXME
        from vm.protocol.mapping import PyMapping  # FIXME

        r = PySequence.from_pyobj(self).length_opt(vm)
        if r is None:
            return PyMapping.from_pyobj(self).length_opt(vm)
        return r

    def length(self, vm: VirtualMachine) -> int:
        r = self.length_opt(vm)
        if r is None:
            vm.new_type_error("object of type '{self}' has no len()")
        return r

    def get_item(self, needle: PyObjectRef, vm: VirtualMachine) -> PyObjectRef:
        import vm.builtins.dict as pydict
        import vm.protocol.mapping as mapping
        import vm.protocol.sequence as sequence

        if dict_ := self.downcast_ref_if_exact(pydict.PyDict, vm):
            return dict_._.get_item(needle, vm)

        # needle = needle.into_pyobj(vm)
        try:
            mapping = mapping.PyMapping.try_protocol(self, vm)
        except PyImplBase:
            pass
        else:
            return mapping.subscript_(needle, vm)

        try:
            seq = sequence.PySequence.try_protocol(self, vm)
        except PyImplBase:
            pass
        else:
            i = needle.key_as_isize(vm)
            return seq.get_item(i, vm)

        if self.class_()._.issubclass(vm.ctx.types.type_type):
            if self.is_(vm.ctx.types.type_type):
                return PyGenericAlias.new(self.clone_class(), needle, vm).into_pyresult(
                    vm
                )

            if (
                class_getitem := vm.get_attribute_opt(
                    self, vm.mk_str("__class_getitem__")
                )
            ) is not None:
                return vm.invoke(class_getitem, FuncArgs([needle]))

        vm.new_type_error(f"'{self.class_()}' object is not subscriptable")

    def set_item(
        self, needle: PyObjectRef, value: PyObjectRef, vm: VirtualMachine
    ) -> None:
        import vm.builtins.dict as pydict  # FIXME
        from vm.protocol.mapping import PyMapping
        from vm.protocol.sequence import PySequence

        if dict_ := self.downcast_ref_if_exact(pydict.PyDict, vm):
            return dict_._.set_item(needle, value, vm)

        mapping = PyMapping.from_pyobj(self)
        seq = PySequence.from_pyobj(self)

        if (f := mapping.methods_(vm).ass_subscript) is not None:
            f(mapping, needle, value, vm)
        elif (f := seq.methods_(vm).ass_item) is not None:
            i = needle.key_as_isize(vm)
            f(seq, i, value, vm)
        else:
            vm.new_type_error(f"'{self.class_()}' does not support item assignment")

    def del_item(self, needle: PyObjectRef, vm: VirtualMachine) -> None:
        from vm.builtins.dict import PyDict

        if dict_ := self.downcast_ref_if_exact(PyDict, vm):
            return dict_._.del_item(needle, vm)

        mapping = PyMapping.from_pyobj(self)
        seq = PySequence.from_pyobj(self)

        if (f := mapping.methods_(vm).ass_subscript) is not None:
            needle = needle.into_pyobj(vm)
            return f(mapping, needle, None, vm)
        elif f := seq.methods_(vm).ass_item:
            i = needle.key_as_isize(vm)
            return f(seq, i, None, vm)
        else:
            vm.new_type_error(f"'{self.class_()}' does not support item deletion")

    def key_as_isize(self, vm: VirtualMachine) -> int:
        return vm.to_index(self)._.try_to_primitive(vm)

    def get_id(self) -> int:
        return id(self._)

    def is_(self, other: Any) -> bool:
        return self.get_id() == other.get_id()

    def payload_(self, t: Type[PT]) -> Optional[PT]:
        if self.payload_is(t):
            return self._  # type: ignore
        else:
            return None

    def payload_if_exact(self, t: Type[PT], vm: VirtualMachine) -> Optional[PT]:
        if self.class_().is_(t.class_(vm)):
            return self.payload_(t)
        else:
            return None

    def payload_unchecked(self, t: Type[PT]) -> PT:
        return self._  # type: ignore

    # TODO: del?
    @classmethod
    def try_from_object(
        cls, t: Type[PT], vm: VirtualMachine, obj: PyObjectRef
    ) -> PyRef[PT]:
        class_ = t.class_(vm)
        if obj.isinstance(class_):
            try:
                return obj.downcast(t)
            except PyImplBase as _:
                pyref_payload_error(vm, class_, obj)
        else:
            r = t.special_retrieve(vm, obj)
            if r is None:
                pyref_payload_error(vm, class_, obj)
            return r

    def is_true(self, vm: VirtualMachine) -> bool:
        return self.try_to_bool(vm)

    def not_(self, vm: VirtualMachine) -> bool:
        return not self.is_true(vm)

    def length_hint(self, defaultvalue: int, vm: VirtualMachine) -> int:
        r = vm.length_hint_opt(self)
        if r is None:
            return defaultvalue
        return r

    def get_iter(self, vm: VirtualMachine) -> PyIter:
        import vm.protocol.iter as viter

        return viter.PyIter.try_from_object(vm, self)

    def hash(self, vm: VirtualMachine) -> PyHash:
        hash = self.class_()._.mro_find_map(lambda cls: cls.slots.hash)
        assert hash is not None, (
            self.class_()._.name(),
            self.class_()._.slots.hash,
        )
        return hash(self, vm)


def pyref_payload_error(
    vm: VirtualMachine, class_: PyTypeRef, obj: PyObjectRef
) -> NoReturn:
    vm.new_runtime_error(
        f"Unexpected payload '{class_._.name()}' for type '{obj.class_()._.name()}'"
    )


def pyref_type_error(vm: VirtualMachine, class_: PyTypeRef, obj: PyObject) -> NoReturn:
    vm.new_type_error(
        "Expected type '{}', not '{}'".format(class_._.name(), obj.class_()._.name())
    )


class PTProtocol(Protocol):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        ...

    # @classmethod
    # def special_retrieve(cls: Type[T], vm: VirtualMachine, obj: PyObjectRef) -> PyRef[T]:
    #     ...

    @classmethod
    def try_from_object(cls: Type[T], vm: VirtualMachine, obj: PyObjectRef) -> PyRef[T]:
        ...


PyObject = PyRef[Any]
PT = TypeVar("PT", bound=PTProtocol)
PyObjectRef = PyObject


def init_type_hierarchy() -> tuple[PyTypeRef, PyTypeRef, PyTypeRef]:
    import vm.pyobject as po
    import vm.builtins.pytype as pytype
    import vm.builtins.object as oo

    # type_payload = pytype.PyType.new_simple_ref("type", None)
    # object_payload = pytype.PyType.new_simple_ref("object", None)
    type_payload = pytype.PyType(
        base=None,
        bases=[],
        mro_=[],
        subclasses=[],
        attributes=po.PyAttributes(),
        slots=pytype.PyType.make_slots(),
    )
    object_payload = pytype.PyType(
        base=None,
        bases=[],
        mro_=[],
        subclasses=[],
        attributes=po.PyAttributes(),
        slots=oo.PyBaseObject.make_slots(),
    )
    type_type = PyRef[pytype.PyType].new_ref(
        type=None, dict=None, payload=type_payload  # type: ignore
    )
    type_type.type = type_type
    object_type = PyRef[pytype.PyType](
        type=type_type, dict=None, payload=object_payload
    )
    type_payload.mro_ = [object_type]
    type_payload.bases = [object_type]
    type_payload.base = object_type

    weakref_type = PyRef.new_ref(
        pytype.PyType(
            base=object_type,
            bases=[object_type],
            mro_=[object_type],
            subclasses=[],
            attributes=po.PyAttributes(),
            slots=po.PyWeak.make_slots(),
        ),
        type_type,
        None,
    )

    # FIXME: make the following work:
    # object_payload.subclasses.append(type_type)
    # object_payload.subclasses.append(weakref_type)
    return type_type, object_type, weakref_type
