from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Optional, TypeAlias

from common.error import PyImplBase, PyImplException, unreachable
from vm.protocol.iter import PyIterReturnStopIteration

if TYPE_CHECKING:
    from vm.builtins.code import PyCode
    from vm.builtins.genericalias import PyGenericAlias
    from vm.builtins.pystr import PyStrRef
    from vm.builtins.pytype import PyTypeRef
    from vm.coroutine import Coro
    from vm.frame import FrameRef
    from vm.protocol.iter import PyIterReturn
    from vm.pyobject import PyContext
    from vm.pyobjectrc import PyObjectRef, PyRef
    from vm.vm import VirtualMachine

from common.deco import pyclassmethod, pymethod, pyproperty
import vm.pyobject as po
import vm.coroutine as coroutine
import vm.builtins.genericalias as pygenericalias
import vm.types.slot as slot


@po.pyimpl(constructor=False)
@po.pyclass("async_generator")
@dataclass
class PyAsyncGen(po.PyClassImpl):
    inner: Coro
    running_async: bool

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.async_generator

    def as_coro(self) -> Coro:
        return self.inner

    @staticmethod
    def new(frame: FrameRef, name: PyStrRef) -> PyAsyncGen:
        return PyAsyncGen(inner=coroutine.Coro.new(frame, name), running_async=False)

    @pyproperty()
    def get_name(self, *, vm: VirtualMachine) -> PyStrRef:
        return self.inner.name

    @pyproperty()
    def set_name(self, name: PyStrRef, *, vm: VirtualMachine) -> None:
        self.inner.set_name(name)

    @pymethod(True)
    @staticmethod
    def i__repr__(zelf: PyRef[PyAsyncGen], *, vm: VirtualMachine) -> str:
        return zelf._.inner.repr(zelf.as_object(), zelf.get_id(), vm)

    @pymethod(True)
    @staticmethod
    def i__aiter__(zelf: PyRef[PyAsyncGen], *, vm: VirtualMachine) -> PyRef[PyAsyncGen]:
        return zelf

    @pymethod(True)
    @staticmethod
    def i__anext__(zelf: PyRef[PyAsyncGen], *, vm: VirtualMachine) -> PyAsyncGenASend:
        return PyAsyncGen.asend(zelf, vm.ctx.get_none(), vm=vm)

    @pymethod(True)
    @staticmethod
    def asend(
        zelf: PyRef[PyAsyncGen], value: PyObjectRef, *, vm: VirtualMachine
    ) -> PyAsyncGenASend:
        return PyAsyncGenASend(ag=zelf, state=AwaitableState.Init, value=value)

    @pymethod(True)
    @staticmethod
    def athrow(
        zelf: PyRef[PyAsyncGen],
        exc_type: PyObjectRef,
        exc_val: Optional[PyObjectRef],
        exc_tb: Optional[PyObjectRef],
        *,
        vm: VirtualMachine,
    ) -> PyAsyncGenAThrow:
        return PyAsyncGenAThrow(
            ag=zelf,
            aclose=False,
            state=AwaitableState.Init,
            value=(exc_type, vm.unwrap_or_none(exc_val), vm.unwrap_or_none(exc_tb)),
        )

    @pymethod(True)
    @staticmethod
    def aclose(zelf: PyRef[PyAsyncGen], *, vm: VirtualMachine) -> PyAsyncGenAThrow:
        return PyAsyncGenAThrow(
            ag=zelf,
            aclose=True,
            state=AwaitableState.Init,
            value=(
                vm.ctx.exceptions.generator_exit.into_pyobj(vm),
                vm.ctx.get_none(),
                vm.ctx.get_none(),
            ),
        )

    @pyproperty()
    def get_ag_await(self, *, vm: VirtualMachine) -> Optional[PyObjectRef]:
        return self.inner.frame._.yield_from_target()

    @pyproperty()
    def get_ag_frame(self, *, vm: VirtualMachine) -> PyObjectRef:
        return self.inner.frame

    @pyproperty()
    def get_ag_running(self, *, vm: VirtualMachine) -> PyObjectRef:
        return vm.ctx.new_bool(self.inner.running)

    @pyproperty()
    def get_ag_code(self, *, vm: VirtualMachine) -> PyObjectRef:
        return self.inner.frame._.code

    @pyclassmethod(True)
    @staticmethod
    def i__getitem__(
        class_: PyTypeRef, args: PyObjectRef, *, vm: VirtualMachine
    ) -> PyGenericAlias:
        return pygenericalias.PyGenericAlias.new(class_, args, vm)


PyAsyncGenRef: TypeAlias = "PyRef[PyAsyncGen]"


@po.pyimpl()
@po.pyclass("async_generator_wrapped_value")
@dataclass
class PyAsyncGenWrappedValue(po.PyClassImpl):
    value: PyObjectRef

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.async_generator_wrapped_value

    @staticmethod
    def unbox(
        ag: PyAsyncGen, get_val: Callable[[], PyIterReturn], vm: VirtualMachine
    ) -> PyObjectRef:

        try:
            val = get_val()
        except PyImplException as e:
            ag.running_async = True
            if e.exception.isinstance(vm.ctx.exceptions.generator_exit):
                ag.inner.closed = True
            else:
                ag.inner.closed = False
            raise
        except PyImplBase as _:
            ag.inner.closed = False
            ag.running_async = True
            raise
        if isinstance(val, PyIterReturnStopIteration):
            ag.inner.closed = ag.running_async = True
        else:
            ag.inner.closed = ag.running_async = False

        val = val.into_async_pyresult(vm)

        # FIXME: match_class!
        try:
            wr = val.downcast(PyAsyncGenWrappedValue)  # match_class!(val @ Self)
        except PyImplBase as _:
            return val
        else:
            ag.running_async = False
            vm.new_stop_iteration(wr._.value)


class AwaitableState(enum.Enum):
    Init = enum.auto()
    Iter = enum.auto()
    Closed = enum.auto()


@po.pyimpl(iter_next=True)
@po.pyclass("async_generator_asend")
@dataclass
class PyAsyncGenASend(
    po.PyClassImpl,
    slot.IterNextMixin,
    slot.IterNextIterableMixin,
):
    ag: PyAsyncGenRef
    state: AwaitableState
    value: PyObjectRef

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.async_generator_asend

    @pymethod(True)
    @staticmethod
    def i__await__(
        zelf: PyRef[PyAsyncGenASend], vm: VirtualMachine
    ) -> PyRef[PyAsyncGenASend]:
        return zelf

    @pymethod(True)
    def send(self, val: PyObjectRef, vm: VirtualMachine) -> PyObjectRef:
        if self.state == AwaitableState.Closed:
            vm.new_runtime_error("cannot reuse already awaited __anext__()/asend()")
        elif self.state == AwaitableState.Iter:
            pass
        elif self.state == AwaitableState.Init:
            if self.ag._.running_async:
                vm.new_runtime_error(
                    "anext(): asynchronous generator is already running"
                )
            self.ag._.running_async = True
            self.state = AwaitableState.Iter
            if vm.is_none(val):
                val = self.value
        else:
            assert False, self.state

        try:
            return PyAsyncGenWrappedValue.unbox(
                self.ag._,
                lambda: self.ag._.inner.send(self.ag, val, vm),
                vm,
            )
        except PyImplBase as _:
            self.close(vm)
            raise
        unreachable()

    @pymethod(True)
    def throw(
        self,
        exc_type: PyObjectRef,
        exc_val: Optional[PyObjectRef],
        exc_tb: Optional[PyObjectRef],
        vm: VirtualMachine,
    ) -> PyObjectRef:
        if self.state == AwaitableState.Closed:
            vm.new_runtime_error("cannot reuse already awaited __anext__()/asend()")

        try:
            return PyAsyncGenWrappedValue.unbox(
                self.ag._,
                lambda: self.ag._.inner.throw(
                    self.ag,
                    exc_type,
                    vm.unwrap_or_none(exc_val),
                    vm.unwrap_or_none(exc_tb),
                    vm,
                ),
                vm,
            )
        except PyImplException as _:
            self.close(vm)
            raise

    @pymethod(True)
    def close(self, vm: VirtualMachine) -> None:
        self.state = AwaitableState.Closed

    @classmethod
    def next(cls, zelf: PyRef[PyAsyncGenASend], vm: VirtualMachine) -> PyIterReturn:
        return PyIterReturn.from_pyresult(
            lambda: zelf._.send(vm.ctx.get_none(), vm), vm
        )


@po.pyimpl(iter_next=True)
@po.pyclass("async_generator_athrow")
@dataclass
class PyAsyncGenAThrow(
    po.PyClassImpl,
    slot.IterNextMixin,
    slot.IterNextIterableMixin,
):
    ag: PyAsyncGenRef
    aclose: bool
    state: AwaitableState
    value: tuple[PyObjectRef, PyObjectRef, PyObjectRef]

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.async_generator_athrow

    @pymethod(True)
    def send(self, val: PyObjectRef, vm: VirtualMachine) -> PyObjectRef:
        raise NotImplementedError

    @pymethod(True)
    def throw(
        self,
        exc_type: PyObjectRef,
        exc_val: Optional[PyObjectRef],
        exc_tb: Optional[PyObjectRef],
        vm: VirtualMachine,
    ) -> PyObjectRef:
        raise NotImplementedError

    @pymethod(True)
    def close(self, vm: VirtualMachine) -> None:
        self.state = AwaitableState.Closed

    @classmethod
    def next(cls, zelf: PyRef[PyAsyncGenAThrow], vm: VirtualMachine) -> PyIterReturn:
        return PyIterReturn.from_pyresult(
            lambda: zelf._.send(vm.ctx.get_none(), vm), vm
        )


def init(ctx: PyContext) -> None:
    PyAsyncGen.extend_class(ctx, ctx.types.async_generator)
    PyAsyncGenWrappedValue.extend_class(ctx, ctx.types.async_generator_wrapped_value)
    PyAsyncGenASend.extend_class(ctx, ctx.types.async_generator_asend)
    PyAsyncGenAThrow.extend_class(ctx, ctx.types.async_generator_athrow)
