from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Generic, TypeVar

if TYPE_CHECKING:
    from vm.builtins.int import PyInt
    from vm.builtins.pytype import PyTypeRef
    from vm.builtins.tuple import PyTupleRef
    from vm.function.arguments import ArgCallable
    from vm.protocol.sequence import PySequenceMethods
    from vm.pyobject import PyContext
    from vm.pyobjectrc import PyObject, PyObjectRef, PyRef
    from vm.vm import VirtualMachine
import vm.pyobject as po
import vm.protocol.sequence as sequence
import vm.function_ as fn

# from vm.protocol.iter import PyIterReturn, PyIterReturnReturn, PyIterReturnStopIteration
import vm.protocol.iter as viter
import vm.types.slot as slot

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
        f: Callable[[T, int], viter.PyIterReturn],
        op: Callable[[PositionIterInternal], None],
    ) -> viter.PyIterReturn:
        if isinstance(self.status, IterStatusActive):
            ret = f(self.status.value, self.position)
            if isinstance(ret, viter.PyIterReturnReturn):
                op(self)
            else:
                self.status = IterStatusExhausted()
            return ret
        else:
            return viter.PyIterReturnStopIteration(None)

    def next(self, f: Callable[[T, int], viter.PyIterReturn]) -> viter.PyIterReturn:
        def inc_pos(zelf: PositionIterInternal) -> None:
            zelf.position += 1

        return self._next(f, inc_pos)

    def rev_next(self, f: Callable[[T, int], viter.PyIterReturn]) -> viter.PyIterReturn:
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
class PySequenceIterator(
    po.PyClassImpl, slot.IterNextMixin, slot.IterNextIterableMixin
):
    seq_methods: PySequenceMethods
    internal: PositionIterInternal[PyObjectRef]

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.iter_type

    @staticmethod
    def new(obj: PyObjectRef, vm: VirtualMachine) -> PySequenceIterator:
        seq = sequence.PySequence.try_protocol(obj, vm)
        seq_methods = seq.methods_(vm)
        return PySequenceIterator(seq_methods, PositionIterInternal.new(obj, 0))

    @classmethod
    def next(
        cls, zelf: PyRef[PySequenceIterator], vm: VirtualMachine
    ) -> viter.PyIterReturn:
        return zelf._.internal.next(
            lambda obj, pos: viter.PyIterReturn.from_getitem_result(
                lambda: sequence.PySequence.with_methods(
                    obj, zelf._.seq_methods
                ).get_item(pos, vm),
                vm,
            )
        )


@po.pyimpl(iter_next=True)
@po.pyclass("callable_iterator")
@dataclass
class PyCallableIterator(
    po.PyClassImpl, slot.IterNextMixin, slot.IterNextIterableMixin
):
    sentinel: PyObjectRef
    status: IterStatusActive[ArgCallable] | IterStatusExhausted

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.callable_iterator

    @staticmethod
    def new(callable: ArgCallable, sentinel: PyObjectRef) -> PyCallableIterator:
        return PyCallableIterator(sentinel, IterStatusActive(callable))

    @classmethod
    def next(
        cls, zelf: PyRef[PyCallableIterator], vm: VirtualMachine
    ) -> viter.PyIterReturn:
        status = zelf._.status
        if isinstance(status, IterStatusActive):
            ret = status.value.invoke(fn.FuncArgs(), vm)
            if vm.bool_eq(ret, zelf._.sentinel):
                zelf._.status = IterStatusExhausted()
                return viter.PyIterReturnStopIteration(None)
            else:
                return viter.PyIterReturnReturn(ret)
        else:
            return viter.PyIterReturnStopIteration(None)


def init(context: PyContext) -> None:
    PySequenceIterator.extend_class(context, context.types.iter_type)
    PyCallableIterator.extend_class(context, context.types.callable_iterator)
