from __future__ import annotations
from dataclasses import dataclass
from operator import length_hint
from typing import TYPE_CHECKING, Callable, Generic, Iterator, Optional, Type, TypeVar
from common.error import PyImplBase, PyImplException, PyImplError

if TYPE_CHECKING:
    from vm.pyobjectrc import PyObjectRef
    from vm.vm import VirtualMachine
    from vm.builtins.iter import PySequenceIterator

T = TypeVar("T")


@dataclass
class PyIter(Generic[T]):
    value: PyObjectRef
    t: Optional[Type[T]]

    def as_ref(self) -> PyObjectRef:
        return self.value

    @staticmethod
    def new(obj: PyObjectRef, t: Optional[Type[T]]) -> PyIter[T]:
        return PyIter(obj, t)

    @staticmethod
    def check(obj: PyObjectRef) -> bool:
        return obj.class_()._.mro_find_map(lambda x: x.slots.iternext) is not None

    def next(self, vm: VirtualMachine) -> PyIterReturn[T]:
        iternext = self.value.class_()._.mro_find_map(lambda x: x.slots.iternext)
        if iternext is None:
            vm.new_type_error(
                f"'{self.value.class_()._.name()}' object is not an iterator"
            )
        return iternext(self.value, vm)

    def iter(self, vm: VirtualMachine) -> PyIterIter[T]:
        length_hint = vm.length_hint_opt(self.as_ref())
        return PyIterIter.new(vm, self.value, length_hint, self.t)

    def iter_without_hint(self, vm: VirtualMachine) -> PyIterIter[T]:
        return PyIterIter(vm, self.value, None, self.t)

    def into_iter(self, vm: VirtualMachine) -> PyIterIter[T]:
        return self.iter(vm)

    def into_object(self) -> PyObjectRef:
        return self.value

    def into_pyobject(self, vm: VirtualMachine) -> PyObjectRef:
        return self.value

    @staticmethod
    def try_from_object(vm: VirtualMachine, obj: PyObjectRef) -> PyIter:
        getiter = obj.class_()._.mro_find_map(lambda x: x.slots.iter)
        if getiter is not None:
            iter = getiter(obj, vm)
            if PyIter.check(iter):
                return PyIter(obj, None)
            else:
                vm.new_type_error(
                    f"iter() returned non-iterator of type '{iter.class_()._.name()}'"
                )
        else:
            try:
                seq_iter = PySequenceIterator.new(obj, vm)
                return PyIter(seq_iter.into_object(vm), None)
            except PyImplError as _:
                vm.new_type_error(f"'{obj.class_()._.name()}' object is not iterable")


@dataclass
class PyIterReturn(Generic[T]):
    @staticmethod
    def from_pyresult(
        result: Callable[[], PyObjectRef], vm: VirtualMachine
    ) -> PyIterReturn:
        try:
            return PyIterReturnReturn(result())
        except PyImplException as err:
            if err.exception.isinstance(vm.ctx.exceptions.stop_iteration):
                return PyIterReturnStopIteration(err.exception._.get_arg(0))
            raise

    @staticmethod
    def from_getitem_result(
        result: Callable[[], PyObjectRef], vm: VirtualMachine
    ) -> PyIterReturn:
        raise NotImplementedError

    def into_async_pyresult(self, vm: VirtualMachine) -> PyObjectRef:
        raise NotImplementedError

    def into_pyresult(
        self: PyIterReturn[PyObjectRef], vm: VirtualMachine
    ) -> PyObjectRef:
        if isinstance(self, PyIterReturnReturn):
            return self.value
        elif isinstance(self, PyIterReturnStopIteration):
            vm.new_stop_iteration(self.value)
        else:
            assert False


@dataclass
class PyIterReturnReturn(PyIterReturn[T]):
    value: T


@dataclass
class PyIterReturnStopIteration(PyIterReturn):
    value: Optional[PyObjectRef]


@dataclass
class PyIterIter(Generic[T]):
    vm: VirtualMachine
    obj: PyObjectRef
    length_hint: Optional[int]
    t: Optional[Type[T]]

    @staticmethod
    def new(
        vm: VirtualMachine,
        obj: PyObjectRef,
        length_hint: Optional[int],
        t: Optional[Type[T]],
    ) -> PyIterIter[T]:
        return PyIterIter(vm, obj, length_hint, t)

    def __iter__(self) -> Iterator[T]:
        return self

    def __next__(self) -> T:
        try:
            iret = PyIter.new(self.obj, self.t).next(self.vm)
        except PyImplBase as e:
            x = None
        else:
            if isinstance(iret, PyIterReturnReturn):
                x = iret.value
            else:
                x = None
        if x is None:
            raise StopIteration
        if self.t is None:
            return x
        return self.t.try_from_object(self.vm, x)  # type: ignore

    # def size_hint(self) -> tuple[int, Optional[int]]:
    #     return (self.length_hint or 0, self.length_hint)
