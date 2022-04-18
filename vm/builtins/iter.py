from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Generic, TypeVar
from vm.protocol.iter import PyIterReturn, PyIterReturnReturn, PyIterReturnStopIteration

if TYPE_CHECKING:
    from vm.builtins.int import PyInt
    from vm.builtins.pytype import PyTypeRef
    from vm.builtins.tuple import PyTupleRef
    from vm.function.arguments import ArgCallable
    from vm.protocol.sequence import PySequenceMethods
    from vm.pyobject import PyClassImpl, PyContext, PyValueMixin, pyclass, pyimpl
    from vm.pyobjectrc import PyObject, PyObjectRef
    from vm.vm import VirtualMachine
import vm.pyobject as po

T = TypeVar("T")


@dataclass
class IterStatusActive(Generic[T]):
    value: T


@dataclass
class IterStatusExhausted:
    pass


@dataclass
class PositionIterInternal(Generic[T]):
    status: IterStatusActive[T] | IterStatusExhausted
    position: int

    @staticmethod
    def new(obj: T, position: int) -> PositionIterInternal[T]:
        return PositionIterInternal(IterStatusActive(obj), position)

    def set_state(
        self, state: PyObjectRef, f: Callable[[T, int], int], vm: VirtualMachine
    ) -> None:
        if isinstance(self.status, IterStatusActive):
            if (i := state.payload_(PyInt)) is not None:
                self.position = f(self.status.value, i.as_int())
            else:
                vm.new_type_error("an integer is required.")

    def _reduce(
        self, func: PyObjectRef, f: Callable[[T], PyObjectRef], vm: VirtualMachine
    ) -> PyTupleRef:
        raise NotImplementedError

    def builtins_iter_reduce(
        self, f: Callable[[T], PyObjectRef], vm: VirtualMachine
    ) -> PyTupleRef:
        iter_ = builtins_iter(vm)
        return self._reduce(iter_, f, vm)

    def builtins_reversed_reduce(
        self, f: Callable[[T], PyObjectRef], vm: VirtualMachine
    ) -> PyTupleRef:
        reversed_ = builtins_reversed(vm)
        return self._reduce(reversed_, f, vm)

    def _next(
        self,
        f: Callable[[T, int], PyIterReturn],
        op: Callable[[PositionIterInternal], None],
    ) -> PyIterReturn:
        if isinstance(self.status, IterStatusActive):
            ret = f(self.status.value, self.position)
            if isinstance(ret, PyIterReturnReturn):
                op(self)
            else:
                self.status = IterStatusExhausted()
            return ret
        else:
            return PyIterReturnStopIteration(None)

    def next(self, f: Callable[[T, int], PyIterReturn]) -> PyIterReturn:
        def inc_pos(zelf: PositionIterInternal) -> None:
            zelf.position += 1

        return self._next(f, inc_pos)

    def rev_next(self, f: Callable[[T, int], PyIterReturn]) -> PyIterReturn:
        def do(zelf: PositionIterInternal) -> None:
            if zelf.position == 0:
                zelf.status = IterStatusExhausted()
            else:
                zelf.position -= 1

        return self._next(f, do)

    def length_hint(self, f: Callable[[T], int]) -> int:
        if isinstance(self.status, IterStatusActive):
            return f(self.status.value) - self.position
        else:
            return 0


def builtins_iter(vm: VirtualMachine) -> PyObject:
    return vm.builtins.get_attr(vm.mk_str("iter"), vm)


def builtins_reversed(vm: VirtualMachine) -> PyObject:
    return vm.builtins.get_attr(vm.mk_str("reversed"), vm)


@po.pyimpl(iter_next=True)
@po.pyclass("iterator")
@dataclass
class PySequenceIterator(po.PyClassImpl, po.PyValueMixin):
    seq_methods: PySequenceMethods
    internal: PositionIterInternal[PyObjectRef]

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.iter_type

    @staticmethod
    def new(obj: PyObjectRef, vm: VirtualMachine) -> PySequenceIterator:
        raise NotImplementedError

    def into_object(self, vm: VirtualMachine) -> PyObjectRef:
        raise NotImplementedError

    # TODO: impl IterNextIterable for PySequenceIterator
    # TODO: impl IterNext for PySequenceIterator


@po.pyimpl(iter_next=True)
@po.pyclass("callable_iterator")
@dataclass
class PyCallableIterator(po.PyClassImpl, po.PyValueMixin):
    sentinel: PyObjectRef
    status: IterStatusActive[ArgCallable] | IterStatusExhausted

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.callable_iterator

    # TODO: impl PyCallableIterator
    # TODO: impl IterNextIterable for PyCallableIterator
    # TODO: impl IterNext for PyCallableIterator


def init(context: PyContext) -> None:
    PySequenceIterator.extend_class(context, context.types.iter_type)
    PyCallableIterator.extend_class(context, context.types.callable_iterator)
