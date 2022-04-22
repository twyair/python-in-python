from __future__ import annotations
from dataclasses import dataclass
import enum
from collections import OrderedDict
from typing import Optional, final, TYPE_CHECKING
from abc import ABC, abstractmethod

# from bytecode.bytecode import CodeFlags
from common.error import PyImplBase, PyImplError, PyImplException
from vm.builtins.asyncgenerator import PyAsyncGenWrappedValue

if TYPE_CHECKING:
    from vm.builtins.coroutine import PyCoroutine
    from vm.builtins.dict import PyDict
    from vm.builtins.list import PyList

    # from vm.builtins.pystr import PyStr
    # from vm.builtins.set import PySet

    from vm.function_ import FuncArgs

    # from bytecode.bytecode import ConversionFlag, RaiseKind
    from vm.frame import ExecutingFrame, ExecutionResult
    from vm.vm import VirtualMachine

import vm.builtins.pystr as pystr
import vm.builtins.set as pyset
import vm.frame as vm_frame
import vm.pyobject as po
import bytecode.bytecode as bytecode


class PyException(Exception):
    msg: str


NameIdx = int


@dataclass(unsafe_hash=True)
class Label:
    value: int


class MakeFunctionFlags(enum.Flag):
    EMPTY = 0
    CLOSURE = enum.auto()
    ANNOTATIONS = enum.auto()
    KW_ONLY_DEFAULTS = enum.auto()
    DEFAULTS = enum.auto()


class ComparisonOperator(enum.Enum):
    Greater = enum.auto()
    GreaterOrEqual = enum.auto()
    Less = enum.auto()
    LessOrEqual = enum.auto()
    Equal = enum.auto()
    NotEqual = enum.auto()
    In = enum.auto()
    NotIn = enum.auto()
    Is = enum.auto()
    IsNot = enum.auto()
    ExceptionMatch = enum.auto()


class BinaryOperator(enum.Enum):
    Power = enum.auto()
    Multiply = enum.auto()
    MatrixMultiply = enum.auto()
    Divide = enum.auto()
    FloorDivide = enum.auto()
    Modulo = enum.auto()
    Add = enum.auto()
    Subtract = enum.auto()
    Lshift = enum.auto()
    Rshift = enum.auto()
    And = enum.auto()
    Xor = enum.auto()
    Or = enum.auto()


class UnaryOperator(enum.Enum):
    Not = enum.auto()
    Invert = enum.auto()
    Minus = enum.auto()
    Plus = enum.auto()


@dataclass
class Instruction(ABC):
    def label_arg(self) -> Optional[Label]:
        return None

    @abstractmethod
    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        ...

    @abstractmethod
    def stack_effect(self, jump: bool) -> int:
        ...

    def unconditional_branch(self) -> bool:
        return isinstance(self, (Jump, Continue, Break, ReturnValue, Raise))


@final
@dataclass
class ImportName(Instruction):
    idx: NameIdx

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        frame.import_(vm, vm.mk_str(frame._get_name(self.idx)))

    def stack_effect(self, jump: bool) -> int:
        return -1


@final
@dataclass
class ImportNameless(Instruction):
    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        frame.import_(vm, None)

    def stack_effect(self, jump: bool) -> int:
        return -1


@final
@dataclass
class ImportStar(Instruction):
    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        frame.import_star(vm)

    def stack_effect(self, jump: bool) -> int:
        return -1


@final
@dataclass
class ImportFrom(Instruction):
    idx: NameIdx

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        obj = frame.import_from(vm, self.idx)
        frame.push_value(obj)

    def stack_effect(self, jump: bool) -> int:
        return 1


@final
@dataclass
class LoadFast(Instruction):
    idx: NameIdx

    def stack_effect(self, jump: bool) -> int:
        return 1

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        x = frame.fastlocals[self.idx]
        if x is None:
            raise PyException(
                # vm.ctx.exceptions.unbound_local_error.clone(),
                f"local variable '{frame.code._.code.varnames[self.idx]}' referenced before assignment"
            )
        frame.push_value(x)


@final
@dataclass
class LoadNameAny(Instruction):
    idx: NameIdx

    def stack_effect(self, jump: bool) -> int:
        return 1

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        name = vm.mk_str(frame._get_name(self.idx))
        map = frame.locals.mapping()
        try:
            value = map.subscript_(name, vm)
        except PyImplBase:
            frame.push_value(frame.load_global_or_builtin(name, vm))
        else:
            frame.push_value(value)


@final
@dataclass
class LoadGlobal(Instruction):
    idx: NameIdx

    def stack_effect(self, jump: bool) -> int:
        return 1

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        name = frame._get_name(self.idx)
        x = frame.load_global_or_builtin(vm.mk_str(name), vm)
        frame.push_value(x)


@final
@dataclass
class LoadDeref(Instruction):
    idx: NameIdx

    def stack_effect(self, jump: bool) -> int:
        return 1

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        x = frame.cells_frees[self.idx]._.contents
        if x is None:
            frame.unbound_cell_exception(self.idx, vm)
        frame.push_value(x)


@final
@dataclass
class LoadClassDeref(Instruction):
    idx: NameIdx

    def stack_effect(self, jump: bool) -> int:
        return 1

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        name = frame.code._.code.freevars[self.idx - len(frame.code._.code.cellvars)]
        try:
            value = frame.locals.mapping().subscript_(name.as_object(), vm)
        except PyImplBase:
            value = frame.cells_frees[self.idx]._.contents
            if value is None:
                frame.unbound_cell_exception(self.idx, vm)
        frame.push_value(value)


@final
@dataclass
class StoreFast(Instruction):
    idx: NameIdx

    def stack_effect(self, jump: bool) -> int:
        return -1

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        value = frame.pop_value()
        frame.fastlocals[self.idx] = value


@final
@dataclass
class StoreLocal(Instruction):
    idx: NameIdx

    def stack_effect(self, jump: bool) -> int:
        return -1

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        name = frame.code._.code.names[self.idx]
        value = frame.pop_value()
        frame.locals.mapping().ass_subscript_(name, value, vm)


@final
@dataclass
class StoreGlobal(Instruction):
    idx: NameIdx

    def stack_effect(self, jump: bool) -> int:
        return -1

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        value = frame.pop_value()
        frame.globals.set_item(frame.code._.code.names[self.idx], value, vm)


@final
@dataclass
class StoreDeref(Instruction):
    idx: NameIdx

    def stack_effect(self, jump: bool) -> int:
        return -1

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        value = frame.pop_value()
        frame.cells_frees[self.idx]._.set(value)


@final
@dataclass
class DeleteFast(Instruction):
    idx: NameIdx

    def stack_effect(self, jump: bool) -> int:
        return 0

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        frame.fastlocals[self.idx] = None


@final
@dataclass
class DeleteLocal(Instruction):
    idx: NameIdx

    def stack_effect(self, jump: bool) -> int:
        return 0

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        name = vm.mk_str(frame._get_name(self.idx))
        map = frame.locals.mapping()
        try:
            map.ass_subscript_(name, None, vm)
        except PyImplException as e:
            if e.exception.isinstance(vm.ctx.exceptions.key_error):
                vm.new_name_error(f"name '{name}' is not defined", name)
            else:
                raise


@final
@dataclass
class DeleteGlobal(Instruction):
    idx: NameIdx

    def stack_effect(self, jump: bool) -> int:
        return 0

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        name = frame.code._.code.names[self.idx]
        try:
            frame.globals.del_item(name, vm)
        except PyImplException as e:
            if e.exception.isinstance(vm.ctx.exceptions.key_error):
                vm.new_name_error(f"name '{name}' is not defined", name)
            else:
                raise


@final
@dataclass
class DeleteDeref(Instruction):
    idx: NameIdx

    def stack_effect(self, jump: bool) -> int:
        return 0

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        frame.cells_frees[self.idx]._.set(None)


@final
@dataclass
class LoadClosure(Instruction):
    idx: NameIdx

    def stack_effect(self, jump: bool) -> int:
        return 1

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        value = frame.cells_frees[self.idx]
        frame.push_value(value)


@final
@dataclass
class Subscript(Instruction):
    def stack_effect(self, jump: bool) -> int:
        return -1

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        return frame.execute_subscript(vm)


@final
@dataclass
class StoreSubscript(Instruction):
    def stack_effect(self, jump: bool) -> int:
        return -3

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        return frame.execute_store_subscript(vm)


@final
@dataclass
class DeleteSubscript(Instruction):
    def stack_effect(self, jump: bool) -> int:
        return -2

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        return frame.execute_delete_subscript(vm)


@final
@dataclass
class StoreAttr(Instruction):
    idx: NameIdx

    def stack_effect(self, jump: bool) -> int:
        return -2

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        return frame.store_attr(vm, self.idx)


@final
@dataclass
class DeleteAttr(Instruction):
    idx: NameIdx

    def stack_effect(self, jump: bool) -> int:
        return -1

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        return frame.delete_attr(vm, self.idx)


@final
@dataclass
class LoadConst(Instruction):
    idx: int

    def stack_effect(self, jump: bool) -> int:
        return 1

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        frame.push_value(frame.code._.code.constants[self.idx].value)


@final
@dataclass
class UnaryOperation(Instruction):
    op: UnaryOperator

    def stack_effect(self, jump: bool) -> int:
        return 0

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        return frame.execute_unop(vm, self.op)


@final
@dataclass
class BinaryOperation(Instruction):
    op: BinaryOperator

    def stack_effect(self, jump: bool) -> int:
        return -1

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        return frame.execute_binop(vm, self.op)


@final
@dataclass
class BinaryOperationInplace(Instruction):
    op: BinaryOperator

    def stack_effect(self, jump: bool) -> int:
        return -1

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        return frame.execute_binop_inplace(vm, self.op)


@final
@dataclass
class LoadAttr(Instruction):
    idx: NameIdx

    def stack_effect(self, jump: bool) -> int:
        return 0

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        return frame.load_attr(vm, self.idx)


@final
@dataclass
class CompareOperation(Instruction):
    op: ComparisonOperator

    def stack_effect(self, jump: bool) -> int:
        return -1

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        return frame.execute_compare(vm, self.op)


@final
@dataclass
class Pop(Instruction):
    def stack_effect(self, jump: bool) -> int:
        return -1

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        frame.pop_value()


@final
@dataclass
class Rotate2(Instruction):
    def stack_effect(self, jump: bool) -> int:
        return 0

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        return frame.execute_rotate(2)


@final
@dataclass
class Rotate3(Instruction):
    def stack_effect(self, jump: bool) -> int:
        return 0

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        return frame.execute_rotate(3)


@final
@dataclass
class Duplicate(Instruction):
    def stack_effect(self, jump: bool) -> int:
        return 1

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        frame.push_value(frame.last_value())


@final
@dataclass
class Duplicate2(Instruction):
    def stack_effect(self, jump: bool) -> int:
        return 2

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        top = frame.pop_value()
        second_to_top = frame.pop_value()
        frame.push_value(second_to_top)
        frame.push_value(top)
        frame.push_value(second_to_top)
        frame.push_value(top)


@final
@dataclass
class GetIter(Instruction):
    def stack_effect(self, jump: bool) -> int:
        return 0

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        iterated_obj = frame.pop_value()
        iter_obj = iterated_obj.get_iter(vm)
        frame.push_value(iter_obj.into_pyobject(vm))


@final
@dataclass
class ReturnValue(Instruction):
    def stack_effect(self, jump: bool) -> int:
        return -1

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        value = frame.pop_value()
        return frame.unwind_blocks(vm, vm_frame.UnwindReturning(value))


@final
@dataclass
class YieldValue(Instruction):
    def stack_effect(self, jump: bool) -> int:
        return 0

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        value = frame.pop_value()
        if bytecode.CodeFlags.IS_COROUTINE in frame.code._.code.flags:
            value = PyAsyncGenWrappedValue(value).into_object(vm)
        return vm_frame.ExecutionResultYield(value)


@final
@dataclass
class YieldFrom(Instruction):
    def stack_effect(self, jump: bool) -> int:
        return -1

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        return frame.execute_yield_from(vm)


@final
@dataclass
class SetupAnnotation(Instruction):
    def stack_effect(self, jump: bool) -> int:
        return 0

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        try:
            d = frame.locals.obj.downcast_exact(PyDict, vm)
        except PyImplError as e:
            needle = vm.mk_str("__annotations__")
            has_annotations = frame._in(vm, needle, e.obj)
        else:
            has_annotations = d._.contains_key(vm.mk_str("__annotations__"), vm)

        if not has_annotations:
            frame.locals.obj.set_item(
                vm.mk_str("__annotations__"), vm.ctx.new_dict(), vm
            )


@final
@dataclass
class Break(Instruction):
    def stack_effect(self, jump: bool) -> int:
        return 0

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        return frame.unwind_blocks(vm, vm_frame.UnwindBreak())


@final
@dataclass
class WithCleanupStart(Instruction):
    def stack_effect(self, jump: bool) -> int:
        return 0

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        block = frame.current_block()
        assert block is not None
        if isinstance(block.type, vm_frame.BlockFinallyHandler):
            reason = block.type.reason
        else:
            frame.fatal("WithCleanupStart expects a FinallyHandler block on stack")

        if reason is not None and isinstance(reason, vm_frame.UnwindRaising):
            exc = reason.exception
        else:
            exc = None

        exit = frame.pop_value()

        if exc is not None:
            args = vm.split_exception(exc)
        else:
            args = [vm.ctx.get_none(), vm.ctx.get_none(), vm.ctx.get_none()]

        exit_res = vm.invoke(exit, FuncArgs(args, OrderedDict()))
        frame.push_value(exit_res)


@final
@dataclass
class WithCleanupFinish(Instruction):
    def stack_effect(self, jump: bool) -> int:
        return -1

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        block = frame.pop_block()
        if isinstance(block.type, vm_frame.BlockFinallyHandler):
            reason = block.type.reason
            prev_exc = block.type.prev_exc
        else:
            frame.fatal("WithCleanupFinish expects a FinallyHandler block on stack")

        suppress_exception = frame.pop_value().try_to_bool(vm)

        vm.set_exception(prev_exc)

        if suppress_exception:
            return None
        elif reason is not None:
            frame.unwind_blocks(vm, reason)
        else:
            return None


@final
@dataclass
class PopBlock(Instruction):
    def stack_effect(self, jump: bool) -> int:
        return 0

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        frame.pop_block()


@final
@dataclass
class PrintExpr(Instruction):
    def stack_effect(self, jump: bool) -> int:
        return -1

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        expr = frame.pop_value()

        try:
            displayhook = vm.sys_module.get_attr(vm.mk_str("displayhook"), vm)
        except PyImplBase:
            vm.new_runtime_error("lost sys.displayhook")

        vm.invoke(displayhook, FuncArgs([expr]))


@final
@dataclass
class LoadBuildClass(Instruction):
    def stack_effect(self, jump: bool) -> int:
        return 1

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        frame.push_value(vm.builtins.get_attr(vm.mk_str("__build_class__"), vm))


@final
@dataclass
class PopException(Instruction):
    def stack_effect(self, jump: bool) -> int:
        return 0

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        block = frame.pop_block()
        if isinstance(block.type, vm_frame.BlockExceptHandler):
            vm.set_exception(block.type.prev_exc)
        else:
            frame.fatal("block type must be ExceptHandler here.")


@final
@dataclass
class GetAwaitable(Instruction):
    def stack_effect(self, jump: bool) -> int:
        return 0

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        awaited_obj = frame.pop_value()
        if awaited_obj.payload_is(PyCoroutine):
            awaitable = awaited_obj
        else:
            await_method = vm.get_method_or_type_error(
                awaited_obj,
                "__await__",
                lambda: f"object {awaited_obj.class_()._.name()} can't be used in 'await' expression",
            )
            awaitable = vm.invoke(await_method, FuncArgs.empty())
        frame.push_value(awaitable)


@final
@dataclass
class BeforeAsyncWith(Instruction):
    def stack_effect(self, jump: bool) -> int:
        return 1

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        mgr = frame.pop_value()
        aexit = mgr.clone().get_attr(vm.mk_str("__aexit__"), vm)
        frame.push_value(aexit)
        aenter_res = vm.call_special_method(mgr, "__aenter__", FuncArgs.empty())
        frame.push_value(aenter_res)


@final
@dataclass
class GetAIter(Instruction):
    def stack_effect(self, jump: bool) -> int:
        return 0

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        aiterable = frame.pop_value()
        aiter = vm.call_special_method(aiterable, "__aiter__", FuncArgs.empty())
        frame.push_value(aiter)


@final
@dataclass
class GetANext(Instruction):
    def stack_effect(self, jump: bool) -> int:
        return 1

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        aiter = frame.last_value()
        awaitable = vm.call_special_method(aiter, "__anext__", FuncArgs.empty())
        if not awaitable.payload_is(PyCoroutine):
            awaitable = vm.call_special_method(awaitable, "__await__", FuncArgs.empty())
        frame.push_value(awaitable)


@final
@dataclass
class EndAsyncFor(Instruction):
    def stack_effect(self, jump: bool) -> int:
        return -2

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        exc = frame.pop_value()
        frame.pop_value()
        if exc.isinstance(vm.ctx.exceptions.stop_async_iteration):
            e = vm.take_exception()
            assert e is not None, "Should have exception in stack"
        else:
            raise PyImplError(exc)


@final
@dataclass
class EnterFinally(Instruction):
    def stack_effect(self, jump: bool) -> int:
        return 0

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        frame.push_block(vm_frame.BlockFinallyHandler(None, vm.current_exception()))


@final
@dataclass
class EndFinally(Instruction):
    def stack_effect(self, jump: bool) -> int:
        return 0

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        block = frame.pop_block()
        if isinstance(block.type, vm_frame.BlockFinallyHandler):
            vm.set_exception(block.type.prev_exc)
            if block.type.reason is not None:
                frame.unwind_blocks(vm, block.type.reason)
        else:
            frame.fatal(
                "Block type must be finally handler when reaching EndFinally instruction!"
            )


@final
@dataclass
class Continue(Instruction):
    target: Label

    def stack_effect(self, jump: bool) -> int:
        return 0

    def label_arg(self) -> Optional[Label]:
        return self.target

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        frame.unwind_blocks(vm, vm_frame.UnwindContinue(self.target))


@final
@dataclass
class Jump(Instruction):
    target: Label

    def stack_effect(self, jump: bool) -> int:
        return 0

    def label_arg(self) -> Optional[Label]:
        return self.target

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        frame.jump(self.target)


@final
@dataclass
class JumpIfTrue(Instruction):
    target: Label

    def stack_effect(self, jump: bool) -> int:
        return -1

    def label_arg(self) -> Optional[Label]:
        return self.target

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        obj = frame.pop_value()
        value = obj.try_to_bool(vm)
        if value:
            frame.jump(self.target)


@final
@dataclass
class JumpIfFalse(Instruction):
    target: Label

    def stack_effect(self, jump: bool) -> int:
        return -1

    def label_arg(self) -> Optional[Label]:
        return self.target

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        obj = frame.pop_value()
        value = obj.try_to_bool(vm)
        if not value:
            frame.jump(self.target)


@final
@dataclass
class JumpIfTrueOrPop(Instruction):
    target: Label

    def stack_effect(self, jump: bool) -> int:
        if jump:
            return 0
        else:
            return -1

    def label_arg(self) -> Optional[Label]:
        return self.target

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        obj = frame.last_value()
        value = obj.try_to_bool(vm)
        if value:
            frame.jump(self.target)
        else:
            frame.pop_value()


@final
@dataclass
class JumpIfFalseOrPop(Instruction):
    target: Label

    def stack_effect(self, jump: bool) -> int:
        if jump:
            return 0
        else:
            return -1

    def label_arg(self) -> Optional[Label]:
        return self.target

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        obj = frame.last_value()
        value = obj.try_to_bool(vm)
        if not value:
            frame.jump(self.target)
        else:
            frame.pop_value()


@final
@dataclass
class CallFunctionPositional(Instruction):
    nargs: int

    def stack_effect(self, jump: bool) -> int:
        return -self.nargs

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        args = frame.collect_positional_args(self.nargs)
        frame.execute_call(args, vm)


@final
@dataclass
class CallFunctionKeyword(Instruction):
    nargs: int

    def stack_effect(self, jump: bool) -> int:
        return -1 - self.nargs

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        args = frame.collect_keyword_args(self.nargs)
        frame.execute_call(args, vm)


@final
@dataclass
class CallMethodPositional(Instruction):
    nargs: int

    def stack_effect(self, jump: bool) -> int:
        return -self.nargs - 3 + 1

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        args = frame.collect_positional_args(self.nargs)
        frame.execute_method_call(args, vm)


@final
@dataclass
class CallMethodKeyword(Instruction):
    nargs: int

    def stack_effect(self, jump: bool) -> int:
        return -1 - self.nargs - 3 + 1

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        args = frame.collect_keyword_args(self.nargs)
        frame.execute_method_call(args, vm)


@final
@dataclass
class MakeFunction(Instruction):
    flags: MakeFunctionFlags

    def stack_effect(self, jump: bool) -> int:
        return (
            -2
            - (MakeFunctionFlags.CLOSURE in self.flags)
            - (MakeFunctionFlags.ANNOTATIONS in self.flags)
            - (MakeFunctionFlags.KW_ONLY_DEFAULTS in self.flags)
            - (MakeFunctionFlags.DEFAULTS in self.flags)
            + 1
        )

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        frame.execute_make_function(vm, self.flags)


@final
@dataclass
class CallFunctionEx(Instruction):
    has_kwargs: bool

    def stack_effect(self, jump: bool) -> int:
        return -1 - self.has_kwargs - 1 + 1

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        args = frame.collect_ex_args(vm, self.has_kwargs)
        frame.execute_call(args, vm)


@final
@dataclass
class LoadMethod(Instruction):
    idx: NameIdx

    def stack_effect(self, jump: bool) -> int:
        return -1 + 3

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        obj = frame.pop_value()
        method_name = frame.code._.code.names[self.idx]
        method = po.PyMethod.get(obj, method_name, vm)
        if isinstance(method, po.PyMethodFunction):
            target, is_method, func = method.target, True, method.func
        elif isinstance(method, po.PyMethodAttribute):
            target, is_method, func = vm.ctx.get_none(), False, method.func
        else:
            assert False, method

        frame.push_value(target)
        frame.push_value(vm.ctx.new_bool(is_method))
        frame.push_value(func)


@final
@dataclass
class CallMethodEx(Instruction):
    has_kwargs: bool

    def stack_effect(self, jump: bool) -> int:
        return -1 - self.has_kwargs - 3 + 1

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        args = frame.collect_ex_args(vm, self.has_kwargs)
        frame.execute_method_call(args, vm)


@final
@dataclass
class ForIter(Instruction):
    target: Label

    def label_arg(self) -> Optional[Label]:
        return self.target

    def stack_effect(self, jump: bool) -> int:
        if jump:
            return -1
        else:
            return 1

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        frame.execute_for_iter(vm, self.target)


@final
@dataclass
class SetupLoop(Instruction):
    target: Label

    def stack_effect(self, jump: bool) -> int:
        return 0

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        frame.push_block(vm_frame.BlockLoop(self.target))


@final
@dataclass
class SetupFinally(Instruction):
    target: Label

    def stack_effect(self, jump: bool) -> int:
        return 0

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        frame.push_block(vm_frame.BlockFinally(self.target))


@final
@dataclass
class SetupExcept(Instruction):
    target: Label

    def stack_effect(self, jump: bool) -> int:
        if jump:
            return 1
        else:
            return 0

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        frame.push_block(vm_frame.BlockTryExcept(self.target))


@final
@dataclass
class SetupWith(Instruction):
    target: Label

    def stack_effect(self, jump: bool) -> int:
        if jump:
            return 0
        else:
            return 1

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        context_manager = frame.pop_value()
        exit = context_manager.get_attr(vm.mk_str("__exit__"), vm)
        frame.push_value(exit)

        enter_res = vm.call_special_method(
            context_manager, "__enter__", FuncArgs.empty()
        )
        frame.push_block(vm_frame.BlockFinally(self.target))
        frame.push_value(enter_res)


@final
@dataclass
class Raise(Instruction):
    kind: bytecode.RaiseKind

    def stack_effect(self, jump: bool) -> int:
        if self.kind == bytecode.RaiseKind.RERAISE:
            return 0
        elif self.kind == bytecode.RaiseKind.RAISE:
            return -1
        elif self.kind == bytecode.RaiseKind.RAISE_CAUSE:
            return -2
        else:
            assert False, self.kind

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        frame.execute_raise(vm, self.kind)


@final
@dataclass
class BuildString(Instruction):
    size: int

    def stack_effect(self, jump: bool) -> int:
        return self.size

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        # FIXME?
        s = [
            pyobj.payload_unchecked(pystr.PyStr).as_str()
            for pyobj in frame.pop_multiple(self.size)
        ]
        str_obj = vm.ctx.new_str("".join(s))
        frame.push_value(str_obj.into_pyobj(vm))


@final
@dataclass
class BuildTuple(Instruction):
    unpack: bool
    size: int

    def stack_effect(self, jump: bool) -> int:
        return self.size

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        elements = frame.get_elements(vm, self.size, self.unpack)
        list_obj = vm.ctx.new_tuple(elements)
        frame.push_value(list_obj)


@final
@dataclass
class BuildList(Instruction):
    unpack: bool
    size: int

    def stack_effect(self, jump: bool) -> int:
        return self.size

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        elements = frame.get_elements(vm, self.size, self.unpack)
        list_obj = vm.ctx.new_list(elements)
        frame.push_value(list_obj)


@final
@dataclass
class BuildSet(Instruction):
    unpack: bool
    size: int

    def stack_effect(self, jump: bool) -> int:
        return self.size

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        set = pyset.PySet.new_ref(vm.ctx)
        elements = frame.pop_multiple(self.size)
        if self.unpack:
            for element in elements:
                vm.map_iterable_object(element, lambda x: set._.add(x, vm=vm))
        else:
            for element in elements:
                set._.add(element, vm=vm)
        frame.push_value(set)


@final
@dataclass
class BuildMap(Instruction):
    unpack: bool
    for_call: bool
    size: int

    def stack_effect(self, jump: bool) -> int:
        nargs = self.size if self.unpack else self.size * 2
        return -nargs + 1

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        return frame.execute_build_map(vm, self.size, self.unpack, self.for_call)


@final
@dataclass
class BuildSlice(Instruction):
    step: bool

    def stack_effect(self, jump: bool) -> int:
        return -2 - self.step + 1

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        return frame.execute_build_slice(vm, self.step)


@final
@dataclass
class ListAppend(Instruction):
    i: int

    def stack_effect(self, jump: bool) -> int:
        return -1

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        obj = frame.nth_value(self.i)
        list_ = obj.downcast_unchecked(PyList)
        item = frame.pop_value()
        list_._.append(item, vm=vm)


@final
@dataclass
class SetAdd(Instruction):
    i: int

    def stack_effect(self, jump: bool) -> int:
        return -1

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        obj = frame.nth_value(self.i)
        set_ = obj.downcast_unchecked(pyset.PySet)
        item = frame.pop_value()
        set_._.add(item, vm=vm)


@final
@dataclass
class MapAdd(Instruction):
    i: int

    def stack_effect(self, jump: bool) -> int:
        return -2

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        obj = frame.nth_value(self.i)
        dict_ = obj.downcast_unchecked(PyDict)
        key = frame.pop_value()
        value = frame.pop_value()
        dict_._.set_item(key, value, vm)


@final
@dataclass
class UnpackSequence(Instruction):
    size: int

    def stack_effect(self, jump: bool) -> int:
        return -1 + self.size

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        value = frame.pop_value()
        try:
            # from vm.pyobjectrc import PyRef
            # assert isinstance(value, PyRef)
            elements = vm.extract_elements_as_pyobjects(value)
        except PyImplException as e:
            if e.exception.class_().is_(vm.ctx.exceptions.type_error):
                vm.new_type_error(
                    f"cannot unpack non-iterable {value.class_()._.name()} object"
                )
            raise

        if len(elements) == self.size:
            frame.state.stack.extend(reversed(elements))
        elif len(elements) > self.size:
            vm.new_value_error(f"too many values to unpack (expected {self.size})")
        else:
            vm.new_value_error(
                f"not enough values to unpack (expected {self.size}, got {len(elements)})"
            )


@final
@dataclass
class UnpackEx(Instruction):
    before: int
    after: int

    def stack_effect(self, jump: bool) -> int:
        return -1 + self.before + 1 + self.after

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        return frame.execute_unpack_ex(vm, self.before, self.after)


@final
@dataclass
class FormatValue(Instruction):
    conversion: bytecode.ConversionFlag

    def stack_effect(self, jump: bool) -> int:
        return -1

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        value = frame.pop_value()
        if self.conversion == bytecode.ConversionFlag.STR:
            value = value.str(vm)
        elif self.conversion == bytecode.ConversionFlag.REPR:
            value = value.repr(vm)
        elif self.conversion == bytecode.ConversionFlag.ASCII:
            raise NotImplementedError
        elif self.conversion == bytecode.ConversionFlag.NONE:
            pass
        else:
            assert False, self.conversion

        spec = frame.pop_value()
        formatted = vm.call_special_method(value, "__format__", FuncArgs([spec]))
        frame.push_value(formatted)


@final
@dataclass
class Reverse(Instruction):
    amount: int

    def stack_effect(self, jump: bool) -> int:
        return 0

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        frame.state.stack[-self.amount :] = reversed(frame.state.stack[-self.amount :])


@final
@dataclass
class SetupAsyncWith(Instruction):
    target: Label

    def stack_effect(self, jump: bool) -> int:
        if jump:
            return -1
        else:
            return 0

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        enter_res = frame.pop_value()
        frame.push_block(vm_frame.BlockFinally(self.target))
        frame.push_value(enter_res)


@final
@dataclass
class MapAddRev(Instruction):
    i: int

    def stack_effect(self, jump: bool) -> int:
        return -2

    def execute(
        self, frame: ExecutingFrame, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        obj = frame.nth_value(self.i)
        dict_ = obj.downcast_unchecked(PyDict)
        value = frame.pop_value()
        key = frame.pop_value()
        dict_._.set_item(key, value, vm)
