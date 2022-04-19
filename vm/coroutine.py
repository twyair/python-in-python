from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Optional

# from vm.frame import ExecutionResult, ExecutionResultReturn, ExecutionResultYield

# from vm.protocol.iter import PyIterReturn, PyIterReturnReturn, PyIterReturnStopIteration


if TYPE_CHECKING:
    from vm.builtins.pystr import PyStrRef
    from vm.exceptions import PyBaseExceptionRef
    from vm.frame import FrameRef
    from vm.vm import VirtualMachine
    from vm.pyobjectrc import PyObject, PyObjectRef

import vm.frame as vframe
import vm.protocol.iter as viter

from common.error import PyImplException, unreachable


def gen_name(gen: PyObject, vm: VirtualMachine) -> str:
    typ = gen.class_()
    if typ.is_(vm.ctx.types.coroutine_type):
        return "coroutine"
    elif typ.is_(vm.ctx.types.async_generator):
        return "async generator"
    else:
        return "generator"


@dataclass
class Coro:
    frame: FrameRef
    closed: bool
    running: bool
    name: PyStrRef
    exception: Optional[PyBaseExceptionRef]

    @staticmethod
    def new(frame: FrameRef, name: PyStrRef) -> Coro:
        return Coro(frame=frame, closed=False, running=False, name=name, exception=None)

    def set_name(self, name: PyStrRef) -> None:
        self.name = name

    def maybe_close(self, res: Optional[vframe.ExecutionResult]) -> None:
        if res is None or isinstance(res, vframe.ExecutionResultReturn):
            self.closed = True

    def run_with_context(
        self,
        gen: PyObject,
        vm: VirtualMachine,
        func: Callable[[FrameRef], vframe.ExecutionResult],
    ):
        if self.running:
            vm.new_value_error("{} already executing".format(gen_name(gen, vm)))
        self.running = True

        vm.push_exception(self.exception)

        result = vm.with_frame(self.frame, func)

        self.exception = vm.pop_exception()

        self.running = False
        return result

    def send(
        self, gen: PyObject, vale: PyObjectRef, vm: VirtualMachine
    ) -> viter.PyIterReturn:
        raise NotImplementedError

    def throw(
        self,
        gen: PyObject,
        exc_type: PyObjectRef,
        exc_val: PyObjectRef,
        exc_tb: PyObjectRef,
        vm: VirtualMachine,
    ) -> viter.PyIterReturn:
        if self.closed:
            raise PyImplException(vm.normalize_exception(exc_type, exc_val, exc_tb))
        try:
            result = self.run_with_context(
                gen, vm, lambda f: f._.gen_throw(vm, exc_type, exc_val, exc_tb)
            )
        except PyImplException as _:
            self.maybe_close(None)
            raise
        self.maybe_close(result)
        return execution_result_into_iter_return(result, vm)

    def close(self, gen: PyObject, vm: VirtualMachine) -> None:
        if self.closed:
            return None
        try:
            result = self.run_with_context(
                gen,
                vm,
                lambda f: f._.gen_throw(
                    vm,
                    vm.ctx.exceptions.generator_exit,
                    vm.ctx.get_none(),
                    vm.ctx.get_none(),
                ),
            )
        except PyImplException as e:
            if not is_gen_exit(e.exception, vm):
                raise
            self.closed = True
        else:
            self.closed = True
            if isinstance(result, vframe.ExecutionResultYield):
                vm.new_runtime_error(
                    "{} ignored GeneratorExit".format(gen_name(gen, vm))
                )
        return None

    def repr(self, gen: PyObject, id: int, vm: VirtualMachine) -> str:
        return "<{} object {} at {:x}>".format(gen_name(gen, vm), self.name, id)


def execution_result_into_iter_return(
    res: vframe.ExecutionResult, vm: VirtualMachine
) -> viter.PyIterReturn:
    if isinstance(res, vframe.ExecutionResultYield):
        return viter.PyIterReturnReturn(res.value)
    elif isinstance(res, vframe.ExecutionResultReturn):
        return viter.PyIterReturnStopIteration(
            None if vm.is_none(res.value) else res.value
        )
    else:
        unreachable()


def is_gen_exit(exc: PyBaseExceptionRef, vm: VirtualMachine) -> bool:
    return exc.isinstance(vm.ctx.exceptions.generator_exit)
