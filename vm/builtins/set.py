from __future__ import annotations
from dataclasses import dataclass
import dataclasses
import inspect
from typing import (
    TYPE_CHECKING,
    Callable,
    ClassVar,
    Iterable,
    Iterator,
    Optional,
    Set,
    TypeAlias,
    TypeVar,
)
from vm.protocol import sequence


if TYPE_CHECKING:
    from vm.builtins.pytype import PyTypeRef
    from vm.pyobject import PyContext
    from vm.pyobjectrc import PyObjectRef, PyRef, PyObject
    from vm.vm import VirtualMachine
    from vm.function.arguments import ArgIterable
    from vm.function_ import FuncArgs

import vm.pyobject as po
import vm.pyobjectrc as prc
import vm.types.slot as slot
import vm.utils as utils
import vm.builtins.iter as pyiter
import vm.builtins.tuple as pytuple
import vm.builtins.dict as pydict
import vm.builtins.genericalias as pygenericalias
import vm.function.arguments as arguments
import vm.protocol.iter as protocol_iter

from vm.dictdatatype import DictContext, DictKey
from common.deco import pyclassmethod, pymethod, pyslot
from common.error import PyImplBase, PyImplError, PyImplException
from common.hash import PyHash, hash_iter_unordered


@po.tp_flags(basetype=True)
@po.pyimpl(as_sequence=True, hashable=False, comparable=True, iterable=True)
@po.pyclass("set")
@dataclass
class PySet(
    po.PyClassImpl,
    slot.ComparableMixin,
    slot.IterableMixin,
    slot.AsSequenceMixin,
):
    inner: PySetInner

    SEQUENCE_METHODS: ClassVar[sequence.PySequenceMethods] = sequence.PySequenceMethods(
        length=lambda s, vm: PySet.sequence_downcast(s)._._len(),
        contains=lambda s, needle, vm: PySet.sequence_downcast(s)._.inner.contains(
            needle, vm=vm
        ),
    )

    @staticmethod
    def new_ref(ctx: PyContext) -> PyRef[PySet]:
        return prc.PyRef.new_ref(PySet.default(), ctx.types.set_type, None)

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.set_type

    @staticmethod
    def default() -> PySet:
        return PySet(PySetInner.default())

    def elements(self) -> list[PyObjectRef]:
        return self.inner.elements()

    def _len(self) -> int:
        return self.inner.len()

    @pyslot
    @staticmethod
    def slot_new(class_: PyTypeRef, args: FuncArgs, vm: VirtualMachine) -> PyObjectRef:
        return PySet.default().into_pyresult_with_type(vm, class_)

    @pymethod(True)
    def i__init__(self, iterable: Optional[ArgIterable], *, vm: VirtualMachine) -> None:
        if self.inner.len() > 0:
            self.inner.clear()

        if iterable is not None:
            self.inner.update(iterable, vm=vm)

    @pymethod(True)
    def i__len__(self, *, vm: VirtualMachine) -> int:
        return self._len()

    @pymethod(True)
    def i__sizeof__(self, *, vm: VirtualMachine) -> int:
        return self.inner.__sizeof__()

    @pymethod(True)
    def i__contains__(self, needle: PyObjectRef, vm: VirtualMachine) -> bool:
        return self.inner.contains(needle, vm=vm)

    @pymethod(True)
    def union(self, *others: ArgIterable, vm: VirtualMachine) -> PyRef[PySet]:
        return PySet(self.inner.union(*others, vm=vm)).into_ref(vm)

    @pymethod(True)
    def intersection(self, *others: ArgIterable, vm: VirtualMachine) -> PyRef[PySet]:
        return PySet(self.inner.intersection(*others, vm=vm)).into_ref(vm)

    @pymethod(True)
    def difference(self, *others: ArgIterable, vm: VirtualMachine) -> PyRef[PySet]:
        return PySet(self.inner.difference(*others, vm=vm)).into_ref(vm)

    @pymethod(True)
    def symmetric_difference(
        self, *others: ArgIterable, vm: VirtualMachine
    ) -> PyRef[PySet]:
        return PySet(self.inner.symmetric_difference(*others, vm=vm)).into_ref(vm)

    @pymethod(True)
    def issubset(self, other: ArgIterable, *, vm: VirtualMachine) -> bool:
        return self.inner.issubset(other, vm=vm)

    @pymethod(True)
    def issuperset(self, other: ArgIterable, *, vm: VirtualMachine) -> bool:
        return self.inner.issuperset(other, vm=vm)

    @pymethod(True)
    def isdisjoint(self, other: ArgIterable, *, vm: VirtualMachine) -> bool:
        return self.inner.isdisjoint(other, vm=vm)

    @pymethod(True)
    def i__or__(
        self, other: PyObjectRef, *, vm: VirtualMachine
    ) -> po.PyArithmeticValue[PyRef[PySet]]:
        try:
            set_iter = SetIterable.try_from_object(vm, other)
        except PyImplBase as _:
            return po.PyArithmeticValue(None)
        else:
            return po.PyArithmeticValue(self.union(*set_iter.iterable, vm=vm))

    @pymethod(True)
    def i__ror__(
        self, other: PyObjectRef, *, vm: VirtualMachine
    ) -> po.PyArithmeticValue[PyRef[PySet]]:
        return self.i__or__(other, vm=vm)

    @pymethod(True)
    def i__and__(
        self, other: PyObjectRef, *, vm: VirtualMachine
    ) -> po.PyArithmeticValue[PyRef[PySet]]:
        try:
            set_iter = SetIterable.try_from_object(vm, other)
        except PyImplBase as _:
            return po.PyArithmeticValue(None)
        else:
            return po.PyArithmeticValue(self.intersection(*set_iter.iterable, vm=vm))

    @pymethod(True)
    def i__rand__(
        self, other: PyObjectRef, *, vm: VirtualMachine
    ) -> po.PyArithmeticValue[PyRef[PySet]]:
        return self.i__and__(other, vm=vm)

    @pymethod(True)
    def i__sub__(
        self, other: PyObjectRef, *, vm: VirtualMachine
    ) -> po.PyArithmeticValue[PyRef[PySet]]:
        try:
            set_iter = SetIterable.try_from_object(vm, other)
        except PyImplBase as _:
            return po.PyArithmeticValue(None)
        else:
            return po.PyArithmeticValue(self.difference(*set_iter.iterable, vm=vm))

    @pymethod(True)
    def i__rsub__(
        self, other: PyObjectRef, *, vm: VirtualMachine
    ) -> po.PyArithmeticValue[PyRef[PySet]]:
        # FIXME?
        return self.i__sub__(other, vm=vm)

    @pymethod(True)
    def i__xor__(
        self, other: PyObjectRef, *, vm: VirtualMachine
    ) -> po.PyArithmeticValue[PyRef[PySet]]:
        try:
            set_iter = SetIterable.try_from_object(vm, other)
        except PyImplBase as _:
            return po.PyArithmeticValue(None)
        else:
            return po.PyArithmeticValue(
                self.symmetric_difference(*set_iter.iterable, vm=vm)
            )

    @pymethod(True)
    def i__rxor__(
        self, other: PyObjectRef, *, vm: VirtualMachine
    ) -> po.PyArithmeticValue[PyRef[PySet]]:
        return self.i__xor__(other, vm=vm)

    @pymethod(True)
    @staticmethod
    def i__repr__(zelf: PyRef[PySet], *, vm: VirtualMachine) -> str:
        raise NotImplementedError

    @pymethod(True)
    def add(self, item: PyObjectRef, *, vm: VirtualMachine) -> None:
        self.inner.add(item, vm=vm)

    @pymethod(True)
    def remove(self, item: PyObjectRef, *, vm: VirtualMachine) -> None:
        self.inner.remove(item, vm=vm)

    @pymethod(True)
    def discard(self, item: PyObjectRef, *, vm: VirtualMachine) -> None:
        self.inner.discard(item, vm=vm)

    @pymethod(True)
    def clear(self, *, vm: VirtualMachine) -> None:
        self.inner.clear()

    @pymethod(True)
    def pop(self, *, vm: VirtualMachine) -> PyObjectRef:
        return self.inner.pop(vm=vm)

    @pymethod(True)
    @staticmethod
    def i__ior__(
        zelf: PyRef[PySet], iterable: SetIterable, *, vm: VirtualMachine
    ) -> PyObjectRef:
        zelf._.inner.update(*iterable.iterable, vm=vm)
        return zelf

    @pymethod(True)
    def update(self, *others: ArgIterable, vm: VirtualMachine) -> None:
        self.inner.update(*others, vm=vm)

    @pymethod(True)
    def intersection_update(self, *others: ArgIterable, vm: VirtualMachine) -> None:
        self.inner.intersection_update(*others, vm=vm)

    @pymethod(True)
    @staticmethod
    def i__iand__(
        zelf: PyRef[PySet], iterable: SetIterable, *, vm: VirtualMachine
    ) -> PyObjectRef:
        zelf._.inner.intersection_update(*iterable.iterable, vm=vm)
        return zelf

    @pymethod(True)
    def difference_update(self, *others: ArgIterable, vm: VirtualMachine) -> None:
        self.inner.difference_update(*others, vm=vm)

    @pymethod(True)
    @staticmethod
    def i__isub__(
        zelf: PyRef[PySet], iterable: SetIterable, *, vm: VirtualMachine
    ) -> PyObjectRef:
        zelf._.inner.difference_update(*iterable.iterable, vm=vm)
        return zelf

    @pymethod(True)
    def symmetric_difference_update(
        self, *others: ArgIterable, vm: VirtualMachine
    ) -> None:
        self.inner.symmetric_difference_update(*others, vm=vm)

    @pymethod(True)
    @staticmethod
    def i__ixor__(
        zelf: PyRef[PySet], iterable: SetIterable, *, vm: VirtualMachine
    ) -> PyObjectRef:
        zelf._.inner.symmetric_difference_update(*iterable.iterable, vm=vm)
        return zelf

    @pymethod(True)
    @staticmethod
    def i__reduce__(zelf: PyRef[PySet], *, vm: VirtualMachine) -> PyObjectRef:
        r = reduce_set(zelf, vm)
        return pytuple.PyTuple([r[0], r[1], vm.unwrap_or_none(r[2])]).into_ref(vm)

    @pyclassmethod(True)
    @staticmethod
    def i__class_getitem__(
        class_: PyTypeRef, args: PyObjectRef, *, vm: VirtualMachine
    ) -> pygenericalias.PyGenericAlias:
        return pygenericalias.PyGenericAlias.new(class_, args, vm)

    @classmethod
    def as_sequence(
        cls, zelf: PyRef[PySet], vm: VirtualMachine
    ) -> sequence.PySequenceMethods:
        return cls.SEQUENCE_METHODS

    @classmethod
    def cmp(
        cls,
        zelf: PyRef[PySet],
        other: PyObject,
        op: slot.PyComparisonOp,
        vm: VirtualMachine,
    ) -> po.PyComparisonValue:
        s = extract_set(other)
        if s is None:
            return po.PyComparisonValue(None)
        return po.PyComparisonValue(zelf._.inner.compare(s, op, vm=vm))

    @classmethod
    def iter(cls, zelf: PyRef[PySet], vm: VirtualMachine) -> PyObjectRef:
        return zelf._.inner.iter().into_object(vm)


@po.tp_flags(basetype=True)
@po.pyimpl(
    as_sequence=True, hashable=True, comparable=True, iterable=True, constructor=True
)
@po.pyclass("frozenset")
@dataclass
class PyFrozenSet(
    po.PyClassImpl,
    slot.AsSequenceMixin,
    slot.HashableMixin,
    slot.ComparableMixin,
    slot.ConstructorMixin,
    slot.IterableMixin,
):
    inner: PySetInner

    SEQUENCE_METHODS: ClassVar[sequence.PySequenceMethods] = sequence.PySequenceMethods(
        length=lambda s, vm: PyFrozenSet.sequence_downcast(s)._._len(),
        contains=lambda s, needle, vm: PyFrozenSet.sequence_downcast(
            s
        )._.inner.contains(needle, vm=vm),
    )

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.frozenset_type

    @staticmethod
    def default() -> PyFrozenSet:
        return PyFrozenSet(PySetInner.default())

    def elements(self) -> list[PyObjectRef]:
        return self.inner.elements()

    @staticmethod
    def from_iter(vm: VirtualMachine, it: Iterator[PyObjectRef]) -> PyFrozenSet:
        return PyFrozenSet(PySetInner.from_iter(it, vm))

    def _len(self) -> int:
        return self.inner.len()

    @pymethod(True)
    def i__len__(self, *, vm: VirtualMachine) -> int:
        return self._len()

    @pymethod(True)
    def i__sizeof__(self, *, vm: VirtualMachine) -> int:
        return self.inner.__sizeof__()

    @pymethod(True)
    @staticmethod
    def copy(zelf: PyRef[PyFrozenSet], *, vm: VirtualMachine) -> PyRef[PyFrozenSet]:
        if zelf.class_().is_(vm.ctx.types.frozenset_type):
            return zelf
        else:
            return PyFrozenSet(zelf._.inner.copy()).into_ref(vm)

    @pymethod(True)
    def i__contains__(self, needle: PyObjectRef, vm: VirtualMachine) -> bool:
        return self.inner.contains(needle, vm=vm)

    @pymethod(True)
    def union(self, *others: ArgIterable, vm: VirtualMachine) -> PyRef[PyFrozenSet]:
        return PyFrozenSet(self.inner.union(*others, vm=vm)).into_ref(vm)

    @pymethod(True)
    def intersection(
        self, *others: ArgIterable, vm: VirtualMachine
    ) -> PyRef[PyFrozenSet]:
        return PyFrozenSet(self.inner.intersection(*others, vm=vm)).into_ref(vm)

    @pymethod(True)
    def difference(
        self, *others: ArgIterable, vm: VirtualMachine
    ) -> PyRef[PyFrozenSet]:
        return PyFrozenSet(self.inner.difference(*others, vm=vm)).into_ref(vm)

    @pymethod(True)
    def symmetric_difference(
        self, *others: ArgIterable, vm: VirtualMachine
    ) -> PyRef[PyFrozenSet]:
        return PyFrozenSet(self.inner.symmetric_difference(*others, vm=vm)).into_ref(vm)

    @pymethod(True)
    def issubset(self, other: ArgIterable, *, vm: VirtualMachine) -> bool:
        return self.inner.issubset(other, vm=vm)

    @pymethod(True)
    def issuperset(self, other: ArgIterable, *, vm: VirtualMachine) -> bool:
        return self.inner.issuperset(other, vm=vm)

    @pymethod(True)
    def isdisjoint(self, other: ArgIterable, *, vm: VirtualMachine) -> bool:
        return self.inner.isdisjoint(other, vm=vm)

    @pymethod(True)
    def i__or__(
        self, other: PyObjectRef, *, vm: VirtualMachine
    ) -> po.PyArithmeticValue[PyRef[PyFrozenSet]]:
        try:
            set_iter = SetIterable.try_from_object(vm, other)
        except PyImplBase as _:
            return po.PyArithmeticValue(None)
        else:
            return po.PyArithmeticValue(self.union(*set_iter.iterable, vm=vm))

    @pymethod(True)
    def i__ror__(
        self, other: PyObjectRef, *, vm: VirtualMachine
    ) -> po.PyArithmeticValue[PyRef[PyFrozenSet]]:
        return self.i__or__(other, vm=vm)

    @pymethod(True)
    def i__and__(
        self, other: PyObjectRef, *, vm: VirtualMachine
    ) -> po.PyArithmeticValue[PyRef[PyFrozenSet]]:
        try:
            set_iter = SetIterable.try_from_object(vm, other)
        except PyImplBase as _:
            return po.PyArithmeticValue(None)
        else:
            return po.PyArithmeticValue(self.intersection(*set_iter.iterable, vm=vm))

    @pymethod(True)
    def i__rand__(
        self, other: PyObjectRef, *, vm: VirtualMachine
    ) -> po.PyArithmeticValue[PyRef[PyFrozenSet]]:
        return self.i__and__(other, vm=vm)

    @pymethod(True)
    def i__sub__(
        self, other: PyObjectRef, *, vm: VirtualMachine
    ) -> po.PyArithmeticValue[PyRef[PyFrozenSet]]:
        try:
            set_iter = SetIterable.try_from_object(vm, other)
        except PyImplBase as _:
            return po.PyArithmeticValue(None)
        else:
            return po.PyArithmeticValue(self.difference(*set_iter.iterable, vm=vm))

    @pymethod(True)
    def i__rsub__(
        self, other: PyObjectRef, *, vm: VirtualMachine
    ) -> po.PyArithmeticValue[PyRef[PyFrozenSet]]:
        # FIXME?
        return self.i__sub__(other, vm=vm)

    @pymethod(True)
    def i__xor__(
        self, other: PyObjectRef, *, vm: VirtualMachine
    ) -> po.PyArithmeticValue[PyRef[PyFrozenSet]]:
        try:
            set_iter = SetIterable.try_from_object(vm, other)
        except PyImplBase as _:
            return po.PyArithmeticValue(None)
        else:
            return po.PyArithmeticValue(
                self.symmetric_difference(*set_iter.iterable, vm=vm)
            )

    @pymethod(True)
    def i__rxor__(
        self, other: PyObjectRef, *, vm: VirtualMachine
    ) -> po.PyArithmeticValue[PyRef[PyFrozenSet]]:
        return self.i__xor__(other, vm=vm)

    @pymethod(True)
    @staticmethod
    def i__repr__(zelf: PyRef[PyFrozenSet], *, vm: VirtualMachine) -> str:
        raise NotImplementedError

    @pymethod(True)
    @staticmethod
    def i__reduce__(zelf: PyRef[PyFrozenSet], *, vm: VirtualMachine) -> PyObjectRef:
        r = reduce_set(zelf, vm)
        return pytuple.PyTuple([r[0], r[1], vm.unwrap_or_none(r[2])]).into_ref(vm)

    @pyclassmethod(True)
    @staticmethod
    def i__class_getitem__(
        class_: PyTypeRef, args: PyObjectRef, *, vm: VirtualMachine
    ) -> pygenericalias.PyGenericAlias:
        return pygenericalias.PyGenericAlias.new(class_, args, vm)

    @classmethod
    def as_sequence(
        cls, zelf: PyRef[PyFrozenSet], vm: VirtualMachine
    ) -> sequence.PySequenceMethods:
        return cls.SEQUENCE_METHODS

    @classmethod
    def hash(cls, zelf: PyRef[PyFrozenSet], vm: VirtualMachine) -> PyHash:
        return zelf._.inner.hash(vm=vm)

    @classmethod
    def cmp(
        cls,
        zelf: PyRef[PyFrozenSet],
        other: PyObject,
        op: slot.PyComparisonOp,
        vm: VirtualMachine,
    ) -> po.PyComparisonValue:
        s = extract_set(other)
        if s is None:
            return po.PyComparisonValue(None)
        return po.PyComparisonValue(zelf._.inner.compare(s, op, vm=vm))

    @classmethod
    def iter(cls, zelf: PyRef[PyFrozenSet], vm: VirtualMachine) -> PyObjectRef:
        return zelf._.inner.iter().into_object(vm)

    @classmethod
    def py_new(
        cls, class_: PyTypeRef, fargs: FuncArgs, /, vm: VirtualMachine
    ) -> PyObjectRef:
        iterable: Optional[PyObjectRef] = fargs.bind(__frozenset_py_new_args).args[0]
        if iterable is not None:
            if class_.is_(vm.ctx.types.frozenset_type):
                try:
                    return iterable.downcast_exact(PyFrozenSet, vm)
                except PyImplError as e:
                    pass
            elements = vm.extract_elements_as_pyobjects(iterable)
        else:
            elements = []

        if not elements and class_.is_(vm.ctx.types.frozenset_type):
            return vm.ctx.empty_frozenset
        else:
            return PyFrozenSet.from_iter(vm, iter(elements)).into_pyresult_with_type(
                vm, class_
            )


def __frozenset_py_new_args(x: Optional[PyObjectRef] = None):
    ...


MT = TypeVar("MT", bound=Callable)


def set_context(method: MT) -> MT:
    sig = inspect.signature(method, eval_str=False)
    p = sig.parameters["vm"]
    assert p.kind == p.KEYWORD_ONLY

    def inner(self, *args, **kwargs):
        self.ctx.vm = kwargs["vm"]
        return method(self, *args, **kwargs)

    return inner  # type: ignore


@dataclass
class PySetInner:
    content: set[DictKey] = dataclasses.field(default_factory=set)
    ctx: DictContext = dataclasses.field(default_factory=lambda: DictContext(None))

    @staticmethod
    def default() -> PySetInner:
        return PySetInner()

    @staticmethod
    def from_iter(iterable: Iterable[PyObjectRef], vm: VirtualMachine) -> PySetInner:
        r = PySetInner()
        r.content = {DictKey(r.ctx, x) for x in iterable}
        return r

    def mk(self, item: PyObjectRef) -> DictKey:
        return DictKey(self.ctx, item)

    def len(self) -> int:
        return len(self.content)

    def copy(self) -> PySetInner:
        return PySetInner(content=self.content.copy())

    @set_context
    def contains(self, needle: PyObject, *, vm: VirtualMachine) -> bool:
        return self.retry_op_with_frozenset(
            needle, vm, lambda needle, vm: self.mk(needle) in self.content
        )

    @set_context
    def compare(
        self, other: PySetInner, op: slot.PyComparisonOp, *, vm: VirtualMachine
    ) -> bool:
        other.ctx.vm = vm
        return op.eval_(self.content, other.content)

    @set_context
    def union(self, other: ArgIterable, *, vm: VirtualMachine) -> PySetInner:
        return PySetInner(self.content.union(self.mk(i) for i in other.iter(vm)))

    @set_context
    def intersection(self, other: ArgIterable, *, vm: VirtualMachine) -> PySetInner:
        return PySetInner(self.content.intersection(self.mk(i) for i in other.iter(vm)))

    @set_context
    def difference(self, other: ArgIterable, *, vm: VirtualMachine) -> PySetInner:
        return PySetInner(self.content.difference(self.mk(i) for i in other.iter(vm)))

    @set_context
    def symmetric_difference(
        self, other: ArgIterable, *, vm: VirtualMachine
    ) -> PySetInner:
        return PySetInner(
            self.content.symmetric_difference(self.mk(i) for i in other.iter(vm))
        )

    @set_context
    def issuperset(self, other: ArgIterable, *, vm: VirtualMachine) -> bool:
        return self.content.issuperset(other.iter(vm))

    @set_context
    def issubset(self, other: ArgIterable, *, vm: VirtualMachine) -> bool:
        return self.content.issubset(other.iter(vm))

    @set_context
    def isdisjoint(self, other: ArgIterable, *, vm: VirtualMachine) -> bool:
        return self.content.isdisjoint(other.iter(vm))

    def iter(self: PySetInner) -> PySetIterator:
        return PySetIterator(
            self.len(),
            pyiter.PositionIterInternal.new(self, 0),
            iter((x.value for x in self.content)),
        )

    def repr(self, class_name: Optional[str], vm: VirtualMachine) -> str:
        return collection_repr(class_name, "{", "}", self.elements(), vm)

    @set_context
    def add(self, item: PyObjectRef, *, vm: VirtualMachine) -> None:
        self.content.add(self.mk(item))

    @set_context
    def remove(self, item: PyObjectRef, *, vm: VirtualMachine) -> None:
        self.retry_op_with_frozenset(
            item, vm, lambda item, vm: self.content.remove(self.mk(item))
        )

    @set_context
    def discard(self, item: PyObjectRef, *, vm: VirtualMachine) -> None:
        self.retry_op_with_frozenset(
            item, vm, lambda item, vm: self.content.discard(self.mk(item))
        )

    def clear(self) -> None:
        self.content.clear()

    def elements(self) -> list[PyObjectRef]:
        return [x.value for x in self.content]

    @set_context
    def pop(self, *, vm: VirtualMachine) -> PyObjectRef:
        r = self.content.pop()
        return r.value

    @set_context
    def update(self, *others: ArgIterable, vm: VirtualMachine) -> None:
        self.content.update(*((self.mk(i) for i in x.iter(vm)) for x in others))

    @set_context
    def intersection_update(self, *others: ArgIterable, vm: VirtualMachine) -> None:
        self.content.intersection_update(
            *((self.mk(i) for i in x.iter(vm)) for x in others)
        )

    @set_context
    def difference_update(self, *others: ArgIterable, vm: VirtualMachine) -> None:
        self.content.difference_update(
            *((self.mk(i) for i in x.iter(vm)) for x in others)
        )

    @set_context
    def symmetric_difference_update(
        self, *others: ArgIterable, vm: VirtualMachine
    ) -> None:
        self.content.symmetric_difference_update(
            *((self.mk(i) for i in x.iter(vm)) for x in others)
        )

    def hash(self, *, vm: VirtualMachine) -> PyHash:
        return hash_iter_unordered(self.elements(), vm)

    def retry_op_with_frozenset(
        self,
        item: PyObject,
        vm: VirtualMachine,
        op: Callable[[PyObject, VirtualMachine], T],
    ) -> T:
        try:
            return op(item, vm)
        except PyImplBase as original_err:
            r = item.payload_if_subclass(PySet, vm)
            if r is None:
                raise
            try:
                return op(PyFrozenSet(r.inner.copy()).into_ref(vm), vm)
            except PyImplException as op_err:
                if op_err.exception.isinstance(vm.ctx.exceptions.key_error):
                    vm.new_key_error(item)
                else:
                    raise


T = TypeVar("T")

# FIXME
SetContentType: TypeAlias = "Set[PyObjectRef]"


def extract_set(obj: PyObject) -> Optional[PySetInner]:
    raise NotImplementedError


def reduce_set(
    zelf: PyObject, vm: VirtualMachine
) -> tuple[PyTypeRef, pytuple.PyTupleRef, Optional[pydict.PyDictRef]]:
    s = extract_set(zelf)
    if s is None:
        s = PySetInner.default()
    if zelf.dict is not None:
        d = zelf.dict.d
    else:
        d = None
    return (zelf.clone_class(), vm.new_tuple([vm.ctx.new_list(s.elements())]), d)


@dataclass
class SetIterable:
    iterable: list[ArgIterable]

    @staticmethod
    def try_from_object(vm: VirtualMachine, obj: PyObjectRef) -> SetIterable:
        class_ = obj.class_()._
        if class_.issubclass(vm.ctx.types.set_type) or class_.issubclass(
            vm.ctx.types.frozenset_type
        ):
            return SetIterable([arguments.ArgIterable.try_from_object(vm, obj)])
        else:
            vm.new_type_error(f"{class_} is not a subtype of set or frozenset")


@po.pyimpl(constructor=False, iter_next=True)
@po.pyclass("set_iterator")
@dataclass
class PySetIterator(
    po.PyClassImpl,
    slot.IterNextMixin,
    slot.IterNextIterableMixin,
):
    size: int
    internal: pyiter.PositionIterInternal[PySetInner]
    iterator: Iterator[PyObjectRef]

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.set_iterator_type

    @pymethod(True)
    def i__length_hint__(self, *, vm: VirtualMachine) -> int:
        return self.internal.length_hint(lambda _: self.size)

    @pymethod(True)
    @staticmethod
    def i__reduce__(zelf: PyRef[PySetIterator], *, vm: VirtualMachine) -> PyObjectRef:
        raise NotImplementedError

    @classmethod
    def next(
        cls, zelf: PyRef[PySetIterator], vm: VirtualMachine
    ) -> protocol_iter.PyIterReturn:
        if isinstance(zelf._.internal.status, pyiter.IterStatusActive):
            if zelf._.internal.status.value.len() != zelf._.size:
                zelf._.impl_extend_class.status = pyiter.IterStatusExhausted()
                vm.new_runtime_error("set changed size during iteration")
            n = next(zelf._.iterator, None)
            if n is None:
                zelf._.internal.status = pyiter.IterStatusExhausted()
                return protocol_iter.PyIterReturnStopIteration(None)
            else:
                return protocol_iter.PyIterReturnReturn(n)
        else:
            return protocol_iter.PyIterReturnStopIteration(None)


def init(context: PyContext) -> None:
    PySet.extend_class(context, context.types.set_type)
    PyFrozenSet.extend_class(context, context.types.frozenset_type)
    PySetIterator.extend_class(context, context.types.set_iterator_type)
