from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, TypeAlias

from common.deco import pyclassmethod, pymethod, pyproperty

if TYPE_CHECKING:
    from vm.builtins.code import PyCode
    from vm.builtins.genericalias import PyGenericAlias
    from vm.builtins.pystr import PyStrRef
    from vm.builtins.pytype import PyTypeRef
    from vm.coroutine import Coro
    from vm.frame import FrameRef
    from vm.protocol.iter import PyIterReturn
    from vm.pyobject import (
        # PyClassImpl,
        PyContext,
        # TryFromObjectMixin,
    )
    from vm.pyobjectrc import PyObject, PyObjectRef, PyRef
    from vm.vm import VirtualMachine

import vm.pyobject as po


@po.pyimpl(constructor=True)
@po.pyclass("async_generator")
@dataclass
class PyAsyncGen(po.TryFromObjectMixin, po.PyClassImpl, po.PyValueMixin):
    inner: Coro
    running_async: bool

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.async_generator

    def as_coro(self) -> Coro:
        return self.inner

    @staticmethod
    def new(frame: FrameRef, name: PyStrRef) -> PyAsyncGen:
        return PyAsyncGen(inner=Coro.new(frame, name), running_async=False)

    @pyproperty()
    def get_name(self) -> PyStrRef:
        return self.inner.name()

    @pyproperty()
    def set_name(self, name: PyStrRef) -> None:
        self.inner.set_name(name)

    @pymethod()
    @staticmethod
    def i__repr__(zelf: PyRef[PyAsyncGen], vm: VirtualMachine) -> str:
        return zelf.payload.inner.repr(zelf.as_object(), zelf.get_id(), vm)

    @pymethod()
    @staticmethod
    def i__aiter__(zelf: PyRef[PyAsyncGen], vm: VirtualMachine) -> PyRef[PyAsyncGen]:
        return zelf

    @pymethod()
    @staticmethod
    def i__anext__(zelf: PyRef[PyAsyncGen], vm: VirtualMachine) -> PyAsyncGenASend:
        return PyAsyncGen.i__asend__(zelf, vm.ctx.get_none(), vm)

    @pymethod()
    @staticmethod
    def i__asend__(
        zelf: PyRef[PyAsyncGen], value: PyObjectRef, vm: VirtualMachine
    ) -> PyAsyncGenASend:
        return PyAsyncGenASend(ag=zelf, state=AwaitableState.Init, value=value)

    @pymethod()
    @staticmethod
    def i__athrow__(
        zelf: PyRef[PyAsyncGen],
        exc_type: PyObjectRef,
        exc_val: OptionalArg,
        exc_tb: OptionalArg,
        vm: VirtualMachine,
    ) -> PyAsyncGenAThrow:
        return PyAsyncGenAThrow(
            ag=zelf,
            aclose=False,
            state=AwaitableState.Init,
            value=(exc_type, exc_val.unwrap_or_none(vm), exc_tb.unwrap_or_none(vm)),
        )

    @pymethod()
    @staticmethod
    def i__aclose__(zelf: PyRef[PyAsyncGen], vm: VirtualMachine) -> PyAsyncGenAThrow:
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
    def get_ag_await(self, vm: VirtualMachine) -> Optional[PyObjectRef]:
        return self.inner.frame().yield_from_target()

    @pyproperty()
    def get_ag_frame(self, vm: VirtualMachine) -> FrameRef:
        return self.inner.frame()

    @pyproperty()
    def get_ag_running(self, vm: VirtualMachine) -> bool:
        return self.inner.running()

    @pyproperty()
    def get_ag_code(self, vm: VirtualMachine) -> PyRef[PyCode]:
        return self.inner.frame().code

    @pyclassmethod()
    @staticmethod
    def i__getitem__(
        class_: PyTypeRef, args: PyObjectRef, vm: VirtualMachine
    ) -> PyGenericAlias:
        return PyGenericAlias.new(class_, args, vm)


PyAsyncGenRef: TypeAlias = "PyRef[PyAsyncGen]"


@po.pyimpl()
@po.pyclass("async_generator_wrapped_value")
@dataclass
class PyAsyncGenWrappedValue(po.TryFromObjectMixin, po.PyClassImpl, po.PyValueMixin):
    value: PyObjectRef

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.async_generator_wrapped_value

    @staticmethod
    def unbox(ag: PyAsyncGen, val: PyIterReturn, vm: VirtualMachine) -> PyObjectRef:
        raise NotImplementedError


# TODO @po.pyimpl PyAsyncGenWrappedvalue


class AwaitableState(enum.Enum):
    Init = enum.auto()
    Iter = enum.auto()
    Closed = enum.auto()


@po.pyimpl(iter_next=True)
@po.pyclass("async_generator_asend")
@dataclass
class PyAsyncGenASend(po.TryFromObjectMixin, po.PyClassImpl, po.PyValueMixin):
    ag: PyAsyncGenRef
    state: AwaitableState
    value: PyObjectRef

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.async_generator_asend


@po.pyimpl(iter_next=True)
@po.pyclass("async_generator_athrow")
@dataclass
class PyAsyncGenAThrow(po.TryFromObjectMixin, po.PyClassImpl, po.PyValueMixin):
    ag: PyAsyncGenRef
    aclose: bool
    state: AwaitableState
    value: tuple[PyObjectRef, PyObjectRef, PyObjectRef]


def init(ctx: PyContext) -> None:
    PyAsyncGen.extend_class(ctx, ctx.types.async_generator)
    PyAsyncGenWrappedValue.extend_class(ctx, ctx.types.async_generator_wrapped_value)
    PyAsyncGenASend.extend_class(ctx, ctx.types.async_generator_asend)
    PyAsyncGenAThrow.extend_class(ctx, ctx.types.async_generator_athrow)
