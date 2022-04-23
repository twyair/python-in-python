from __future__ import annotations

from abc import ABC
from collections import OrderedDict
from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Callable,
    NoReturn,
    Optional,
    TypeAlias,
    TypeVar,
    final,
)
from common import debug_repr

if TYPE_CHECKING:
    from bytecode.bytecode import CodeFlags, Label, Location, RaiseKind

    from vm.builtins.dict import PyDict, PyDictRef

    # from vm.builtins.function import PyCell, PyFunction
    from vm.builtins.pytype import PyTypeRef
    from vm.builtins.slice import PySlice
    from vm.builtins.tuple import PyTuple, PyTupleTyped
    from vm.exceptions import ExceptionCtor, PyBaseExceptionRef
    from vm.function.arguments import ArgMapping
    from vm.function_ import FuncArgs
    from vm.protocol.iter import (
        PyIter,
        PyIterReturn,
        PyIterReturnReturn,
        PyIterReturnStopIteration,
    )

    from vm.pyobjectrc import PyObject, PyObjectRef, PyRef
    from vm.scope import Scope
    from vm.coroutine import Coro
    from vm.vm import VirtualMachine

from common.deco import pymethod, pyproperty
from common.error import PyImplBase, PyImplError, PyImplErrorStr, PyImplException

import vm.pyobject as po
import vm.pyobjectrc as prc
import vm.function_ as fn
import vm.builtins.code as pycode
import vm.builtins.traceback as pytraceback
import vm.builtins.dict as pydict
import vm.builtins.function as pyfunction
import vm.types.slot as slot
import vm.builtins.int as pyint
import vm.builtins.tuple as pytuple
import vm.builtins.pystr as pystr
import bytecode.instruction as instruction
import vm.protocol.iter as viter


@dataclass
class Block:
    type: BlockType
    level: int


@dataclass
class BlockType(ABC):
    pass


@final
@dataclass
class BlockLoop(BlockType):
    break_target: Label


@final
@dataclass
class BlockTryExcept(BlockType):
    handler: Label


@final
@dataclass
class BlockFinally(BlockType):
    handler: Label


@final
@dataclass
class BlockFinallyHandler(BlockType):
    reason: Optional[UnwindReason]
    prev_exc: Optional[PyBaseExceptionRef]


@final
@dataclass
class BlockExceptHandler(BlockType):
    prev_exc: Optional[PyBaseExceptionRef]


@dataclass
class UnwindReason(ABC):
    pass


@final
@dataclass
class UnwindReturning(UnwindReason):
    value: PyObjectRef


@final
@dataclass
class UnwindRaising(UnwindReason):
    exception: PyBaseExceptionRef


@final
@dataclass
class UnwindBreak(UnwindReason):
    pass


@final
@dataclass
class UnwindContinue(UnwindReason):
    target: Label


@final
@dataclass
class FrameState:
    stack: list[PyObjectRef]
    blocks: list[Block]
    # lasti: int


Lasti = int


@final
@po.pyimpl(py_ref=True, constructor=False)
@po.pyclass("frame")
@dataclass
class Frame(po.PyClassImpl):
    code: PyRef[pycode.PyCode]
    fastlocals: list[Optional[PyObjectRef]]
    cells_frees: list[PyCellRef]
    locals: ArgMapping
    globals: PyDictRef
    builtins: PyDictRef
    lasti: Lasti
    trace: PyObjectRef
    state: FrameState

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.frame_type

    @staticmethod
    def new(
        code: PyRef[pycode.PyCode],
        scope: Scope,
        builtins: PyDictRef,
        closure: list[PyCellRef],
        vm: VirtualMachine,
    ) -> Frame:
        cells_frees = [
            pyfunction.PyCell.default().into_ref(vm)
            for _ in range(len(code._.code.cellvars))
        ] + closure
        state = FrameState(stack=[], blocks=[])
        return Frame(
            fastlocals=[None] * len(code._.code.varnames),
            code=code,
            cells_frees=cells_frees,
            locals=scope.locals,
            globals=scope.globals,
            builtins=builtins,
            lasti=0,
            state=state,
            trace=vm.ctx.get_none(),
        )

    def into_ref(self, vm: VirtualMachine) -> FrameRef:
        return prc.PyRef[Frame](vm.ctx.types.frame_type, None, self)

    def with_exec(
        self: Frame, f: Callable[[ExecutingFrame], R], vm: VirtualMachine
    ) -> R:
        return f(
            ExecutingFrame(
                code=self.code,
                fastlocals=self.fastlocals,
                cells_frees=self.cells_frees,
                locals=self.locals,
                globals=self.globals,
                builtins=self.builtins,
                lasti=self.lasti,
                object=prc.PyRef.new_ref(self, vm.ctx.types.frame_type, None),
                state=self.state,
            )
        )

    def get_locals(self, vm: VirtualMachine) -> ArgMapping:
        # `fn locals() ...`
        code = self.code._.code
        map = code.varnames
        j = len(map)  # FIXME?
        # j = min(len(map), len(code.))
        if code.varnames:
            fastlocals = self.fastlocals
            for k, v in zip(map[:j], fastlocals):
                try:
                    self.locals.mapping().ass_subscript_(k, v, vm)
                except PyImplException as e:
                    if not e.exception.isinstance(vm.ctx.exceptions.key_error):
                        raise
        if code.cellvars or code.freevars:

            def map_to_dict(keys: list[pystr.PyStrRef], values: list[PyCellRef]):
                for k, v in zip(keys, values):
                    value = v._.contents
                    if value is not None:
                        self.locals.mapping().ass_subscript_(k.as_object(), value, vm)
                    else:
                        try:
                            self.locals.mapping().ass_subscript_(
                                k.as_object(), None, vm
                            )
                        except PyImplException as e:
                            if not e.exception.isinstance(vm.ctx.exceptions.key_error):
                                raise

            map_to_dict(code.cellvars, self.cells_frees)
            if CodeFlags.IS_OPTIMIZED in code.flags:
                map_to_dict(code.freevars, self.cells_frees[len(code.cellvars) :])
        return self.locals

    def run(self, vm: VirtualMachine) -> ExecutionResult:
        return self.with_exec(lambda exec: exec.run(vm), vm)

    def resume(
        self, value: Optional[PyObjectRef], vm: VirtualMachine
    ) -> ExecutionResult:
        def do(exec: ExecutingFrame) -> ExecutionResult:
            if value is not None:
                exec.push_value(value)
            return exec.run(vm)

        return self.with_exec(do, vm)

    def gen_throw(
        self,
        vm: VirtualMachine,
        exc_type: PyObjectRef,
        exc_val: PyObjectRef,
        exc_tb: PyObjectRef,
    ) -> ExecutionResult:
        return self.with_exec(
            lambda exec: exec.gen_throw(vm, exc_type, exc_val, exc_tb), vm
        )

    def current_location(self) -> Location:
        return self.code._.code.locations[self.lasti - 1]

    def yield_from_target(self, vm: VirtualMachine) -> Optional[PyObjectRef]:
        return self.with_exec(lambda exec: exec.yield_from_target(), vm)

    def get_lasti(self) -> int:
        return self.lasti

    @pymethod(True)
    def i__repr__(self, *, vm: VirtualMachine) -> str:
        return "<frame object at .. >"

    @pymethod(True)
    def i__delattr__(self, value: pystr.PyStrRef, /, *, vm: VirtualMachine) -> None:
        if value._.as_str() == "f_trace":
            self.set_f_trace(vm.ctx.get_none(), vm=vm)

    @pymethod(True)
    def clear(self, *, vm: VirtualMachine) -> None:
        raise NotImplementedError("TODO")

    @pyproperty()
    def get_f_globals(self, *, vm: VirtualMachine) -> PyDictRef:
        return self.globals

    @pyproperty()
    def get_f_locals(self, *, vm: VirtualMachine) -> PyObjectRef:
        raise NotImplementedError
        # return [x.into_pyobject() for x in self.get_locals(vm)]

    @pyproperty()
    def get_f_code(self, *, vm: VirtualMachine) -> PyRef[pycode.PyCode]:
        return self.code

    @pyproperty()
    def get_f_back(self, *, vm: VirtualMachine) -> Optional[PyRef[Frame]]:
        fs = reversed(vm.frames)
        while not next(fs).is_(self):
            pass
        return next(fs)

    @pyproperty()
    def get_f_lasti(self, *, vm: VirtualMachine) -> int:
        return self.get_lasti()

    @pyproperty()
    def get_f_lineno(self, *, vm: VirtualMachine) -> int:
        return self.current_location().row

    @pyproperty()
    def get_f_trace(self, *, vm: VirtualMachine) -> PyObjectRef:
        return self.trace

    @pyproperty()
    def set_f_trace(self, value: PyObjectRef, /, *, vm: VirtualMachine) -> None:
        self.trace = value


R = TypeVar("R")


@dataclass
class ExecutionResult:
    pass


@final
@dataclass
class ExecutionResultReturn(ExecutionResult):
    value: PyObjectRef


@final
@dataclass
class ExecutionResultYield(ExecutionResult):
    value: PyObjectRef


PyCellRef: TypeAlias = "PyRef[pyfunction.PyCell]"


@final
@dataclass
class ExecutingFrame:
    code: PyRef[pycode.PyCode]
    fastlocals: list[Optional[PyObjectRef]]
    cells_frees: list[PyCellRef]
    locals: ArgMapping
    globals: PyDictRef
    builtins: PyDictRef
    object: PyRef[Frame]
    lasti: Lasti
    state: FrameState

    def unbound_cell_exception(
        self, i: instruction.NameIdx, vm: VirtualMachine
    ) -> NoReturn:
        if i < len(self.code._.code.cellvars):
            name = self.code._.code.cellvars[i]
            vm.new_exception_msg(
                vm.ctx.exceptions.unbound_local_error,
                f"local variable '{name}' referenced before assignment",
            )
        else:
            name = self.code._.code.freevars[i - len(self.code._.code.cellvars)]
            vm.new_name_error(
                f"free variable '{name}' referenced before assignment in enclosing scope",
                name,
            )

    def update_lasti(self, f: Callable[[int], int]) -> None:
        self.lasti = f(self.lasti)

    def get_lasti(self) -> int:
        return self.lasti

    def run(self, vm: VirtualMachine) -> ExecutionResult:
        instrs = self.code._.code.instructions
        # print(instrs)
        while 1:
            idx = self.get_lasti()
            self.update_lasti(lambda i: i + 1)
            assert idx < len(instrs), (idx, instrs)
            instr = instrs[idx]
            try:
                # print([type(v) for v in self.state.stack])
                # print([v.class_()._.name() for v in self.state.stack])
                # print(instr)
                result = self.execute_instruction(instr, vm)
                if result is None:
                    continue
                return result
            except PyImplException as e:
                loc = self.code._.code.locations[idx]
                next_ = e.exception._.traceback  # TODO
                new_traceback = pytraceback.PyTraceback.new(
                    next_, self.object, self.get_lasti(), loc.row
                )
                e.exception._.traceback = new_traceback.into_ref(vm)
                vm.contextualize_exception(e.exception)
                result = self.unwind_blocks(vm, UnwindRaising(e.exception))
                if result is None:
                    continue
                else:
                    return result
        assert False

    def yield_from_target(self) -> Optional[PyObject]:
        if isinstance(
            self.code._.code.instructions[self.get_lasti()], instruction.YieldFrom
        ):
            return self.last_value_ref()
        return None

    def gen_throw(
        self,
        vm: VirtualMachine,
        exc_type: PyObjectRef,
        exc_val: PyObjectRef,
        exc_tb: PyObjectRef,
    ) -> ExecutionResult:
        # gen = self.yield_from_target()
        # if gen is not None:
        #     pass
        raise NotImplementedError

    def execute_instruction(
        self, instruction: instruction.Instruction, vm: VirtualMachine
    ) -> Optional[ExecutionResult]:
        # print(instruction, getattr(self.current_block(), "type", None))
        vm.check_signals()

        return instruction.execute(self, vm)

    def load_global_or_builtin(
        self, name: pystr.PyStrRef, vm: VirtualMachine
    ) -> PyObjectRef:
        r = self.globals._.get_chain(self.builtins._, name, vm)
        if r is None:
            vm.new_name_error(f"name '{name._.as_str()}' is not defined", name)
        return r

    def get_elements(
        self, vm: VirtualMachine, size: int, unpack: bool
    ) -> list[PyObjectRef]:
        elements = self.pop_multiple(size)
        if unpack:
            result = []
            for element in elements:
                result.extend(vm.extract_elements_as_pyobjects(element))
            return result
        else:
            return elements

    def import_(
        self, vm: VirtualMachine, module: Optional[pystr.PyStrRef]
    ) -> FrameResult:
        module = module if module is not None else pystr.PyStr.from_str("", vm.ctx)
        try:
            from_list = pytuple.PyTupleTyped[pystr.PyStr].try_from_object(
                pystr.PyStr, vm, self.pop_value()
            )
        except PyImplBase as _:
            from_list = None
        level = pyint.PyInt.try_from_object(vm, self.pop_value())
        self.push_value(vm.import_(module, from_list, level._.as_int()))
        return None

    def import_from(self, vm: VirtualMachine, idx: instruction.NameIdx) -> PyObjectRef:
        module = self.last_value()
        name = self.code._.code.names[idx]
        if (obj := vm.get_attribute_opt(module, name)) is not None:
            return obj
        try:
            mod_name = module.get_attr(vm.mk_str("__name__"), vm).downcast(pystr.PyStr)
            full_mod_name = f"{mod_name}.{name}"
            sys_modules = vm.sys_module.get_attr(vm.mk_str("modules"), vm)
            return sys_modules.get_item(vm.mk_str(full_mod_name), vm)
        except PyImplBase:
            vm.new_import_error(f"cannot import name '{name}'", name)

    def import_star(self, vm: VirtualMachine) -> FrameResult:
        module = self.pop_value()
        if module.dict is not None:
            if (all := module.dict.get_item(vm.mk_str("__all__"), vm)) is not None:
                all_ = [name.as_str() for name in vm.extract_elements(pystr.PyStr, all)]
                filter_pred = lambda name: name in all_
            else:
                filter_pred = lambda name: name.startswith("_")
            for k, v in module.dict.d._.entries.items():
                k = pystr.PyStr.try_from_object(vm, k)
                if filter_pred(k._.as_str()):
                    self.locals.mapping().ass_subscript_(k, v, vm)
        else:
            return None

    def unwind_blocks(self, vm: VirtualMachine, reason: UnwindReason) -> FrameResult:
        while (block := self.current_block()) is not None:
            if isinstance(block.type, BlockLoop):
                if isinstance(reason, UnwindBreak):
                    self.pop_block()
                    self.jump(block.type.break_target)
                    return None
                elif isinstance(reason, UnwindContinue):
                    self.jump(reason.target)
                    return None
                else:
                    self.pop_block()
            elif isinstance(block.type, BlockFinally):
                self.pop_block()
                prev_exc = vm.current_exception()
                if isinstance(reason, UnwindRaising):
                    vm.set_exception(reason.exception.clone())
                self.push_block(BlockFinallyHandler(reason=reason, prev_exc=prev_exc))
                self.jump(block.type.handler)
                return None
            elif isinstance(block.type, BlockTryExcept):
                self.pop_block()
                if isinstance(reason, UnwindRaising):
                    self.push_block(BlockExceptHandler(vm.current_exception()))
                    vm.contextualize_exception(reason.exception)
                    vm.set_exception(reason.exception.clone())
                    self.push_value(reason.exception.into_pyobj(vm))
                    self.jump(block.type.handler)
                    return None
            elif isinstance(block.type, (BlockFinallyHandler, BlockExceptHandler)):
                self.pop_block()
                vm.set_exception(block.type.prev_exc)

        if isinstance(reason, UnwindRaising):
            raise PyImplException(reason.exception)
        elif isinstance(reason, UnwindReturning):
            return ExecutionResultReturn(reason.value)
        elif isinstance(reason, (UnwindBreak, UnwindContinue)):
            self.fatal("break or continue must occur within a loop block.")
        else:
            assert False

    def _get_name(self, idx: instruction.NameIdx) -> str:
        return self.code._.code.names[idx]._.as_str()

    def load_attr(self, vm: VirtualMachine, attr: instruction.NameIdx) -> FrameResult:
        attr_name = self._get_name(attr)
        parent = self.pop_value()
        obj = parent.get_attr(vm.mk_str(attr_name), vm)
        self.push_value(obj)

    def store_attr(self, vm: VirtualMachine, attr: instruction.NameIdx) -> FrameResult:
        attr_name = self._get_name(attr)
        parent = self.pop_value()
        value = self.pop_value()
        parent.set_attr(vm.mk_str(attr_name), value, vm)

    def delete_attr(self, vm: VirtualMachine, attr: instruction.NameIdx) -> FrameResult:
        attr_name = self._get_name(attr)
        parent = self.pop_value()
        parent.del_attr(vm.mk_str(attr_name), vm)

    def push_block(self, type: BlockType) -> None:
        self.state.blocks.append(Block(type, len(self.state.stack)))

    def pop_block(self) -> Block:
        block = self.state.blocks.pop()
        del self.state.stack[block.level :]
        return block

    def current_block(self) -> Optional[Block]:
        if self.state.blocks:
            return self.state.blocks[-1]
        return None

    def push_value(self, obj: PyObjectRef) -> None:

        from vm.pyobjectrc import PyRef

        assert isinstance(obj, PyRef)
        if len(self.state.stack) >= self.code._.code.max_stacksize:
            self.fatal("tried to push value onto stack but overflowed max_stacksize")
        self.state.stack.append(obj)
        # print([debug_repr(x) for x in self.state.stack])

    def pop_value(self) -> PyObjectRef:
        return self.state.stack.pop()

    def pop_multiple(self, count: int) -> list[PyObjectRef]:
        if count == 0:
            return []
        res = self.state.stack[-count:]
        del self.state.stack[-count:]
        return res

    def last_value(self) -> PyObjectRef:
        return self.state.stack[-1]

    def last_value_ref(self) -> PyObject:
        return self.state.stack[-1]

    def nth_value(self, depth: int) -> PyObjectRef:
        return self.state.stack[-depth - 1]

    def fatal(self, msg: str) -> NoReturn:
        assert False, (msg, self)

    def execute_rotate(self, amount: int) -> FrameResult:
        self.state.stack[-amount:-amount] = [self.state.stack[-1]]
        self.state.stack.pop()

    def execute_subscript(self, vm: VirtualMachine) -> FrameResult:
        b_ref = self.pop_value()
        a_ref = self.pop_value()
        value = a_ref.get_item(b_ref, vm)
        self.push_value(value)

    def execute_store_subscript(self, vm: VirtualMachine) -> FrameResult:
        idx = self.pop_value()
        obj = self.pop_value()
        value = self.pop_value()
        obj.set_item(idx, value, vm)

    def execute_delete_subscript(self, vm: VirtualMachine) -> FrameResult:
        idx = self.pop_value()
        obj = self.pop_value()
        obj.del_item(idx, vm)

    def execute_build_map(
        self, vm: VirtualMachine, size: int, unpack: bool, for_call: bool
    ) -> FrameResult:
        map_obj = vm.ctx.new_dict()
        if unpack:
            for obj in self.pop_multiple(size):
                try:
                    dict_ = obj.downcast(PyDict)
                except PyImplBase:
                    vm.new_type_error(
                        f"'{obj.class_()._.name()}' object is not a mapping"
                    )
                for key, value in dict_._.entries.items():
                    if for_call:
                        if map_obj._.contains_key(key, vm):
                            key_repr = key.repr(vm)
                            vm.new_type_error(
                                f"got multiple values for keyword argument {key_repr._.as_str()}"
                            )
                    map_obj._.set_item(key, value, vm)
        else:
            objs = self.pop_multiple(2 * size)
            for key, value in zip(objs[::2], objs[1::2]):
                map_obj.set_item(key, value, vm)
        self.push_value(map_obj.into_pyobj(vm))

    def execute_build_slice(self, vm: VirtualMachine, step: bool) -> FrameResult:
        step_ = self.pop_value() if step else None
        stop = self.pop_value()
        start = self.pop_value()

        obj = prc.PyRef.new_ref(
            PySlice(start=start, stop=stop, step=step_), vm.ctx.types.slice_type, None
        )
        self.push_value(obj)

    def collect_positional_args(self, nargs: int) -> FuncArgs:
        return fn.FuncArgs(args=self.pop_multiple(nargs), kwargs=OrderedDict())

    def collect_keyword_args(self, nargs: int) -> FuncArgs:
        kwarg_names = self.pop_value().downcast(pytuple.PyTuple)
        args = self.pop_multiple(nargs)
        kwarg_names = [pyobj._.as_str() for pyobj in kwarg_names._.elements]
        return fn.FuncArgs.with_kwargs_names(args, kwarg_names)

    def collect_ex_args(self, vm: VirtualMachine, has_kwargs: bool) -> FuncArgs:
        kwargs = OrderedDict()
        if has_kwargs:
            try:
                kw_dict = self.pop_value().downcast(PyDict)
            except PyImplBase:
                vm.new_type_error("Kwargs must be a dict.")
            # // TODO: check collections.abc.Mapping
            for key, value in kw_dict._.entries.items():
                key = key.payload_if_subclass(pystr.PyStr, vm)
                if key is None:
                    vm.new_type_error("keywords must be strings")
                kwargs[key.as_str()] = value
        args = vm.extract_elements_as_pyobjects(self.pop_value())
        return FuncArgs(args, kwargs)

    def execute_call(self, args: FuncArgs, vm: VirtualMachine) -> FrameResult:
        func_ref = self.pop_value()
        value = vm.invoke(func_ref, args)
        self.push_value(value)

    def execute_method_call(self, args: FuncArgs, vm: VirtualMachine) -> FrameResult:
        func = self.pop_value()
        is_method = self.pop_value().is_(vm.ctx.true_value)
        target = self.pop_value()
        if is_method:
            method = po.PyMethodFunction(target=target, func=func)
        else:
            method = po.PyMethodAttribute(func)
        value = method.invoke(args, vm)
        self.push_value(value)

    def execute_raise(self, vm: VirtualMachine, kind: RaiseKind) -> FrameResult:
        cause = None
        if kind == RaiseKind.RAISE_CAUSE:
            val = self.pop_value()
            if not vm.is_none(val):
                try:
                    ctor = ExceptionCtor.try_from_object(vm, val)
                except PyImplError as _:
                    vm.new_type_error("exception causes must derive from BaseException")
                cause = ctor.instantiate(vm)
        if kind == RaiseKind.RERAISE:
            exception = vm.topmost_exception()
            if exception is None:
                vm.new_runtime_error("No active exception to reraise")
        else:
            exception = ExceptionCtor.try_from_object(vm, self.pop_value()).instantiate(
                vm
            )
        if kind == RaiseKind.RAISE_CAUSE:
            exception._.set_cause(cause)
        raise PyImplException(exception)

    def builtin_coro(self, coro: PyObject) -> Optional[Coro]:
        raise NotImplementedError

    def _send(
        self, gen: PyObject, val: PyObjectRef, vm: VirtualMachine
    ) -> PyIterReturn:
        raise NotImplementedError

    def execute_yield_from(self, vm: VirtualMachine) -> Optional[ExecutionResult]:
        val = self.pop_value()
        coro = self.last_value_ref()
        result = self._send(coro, val, vm)

        if isinstance(result, ExecutionResultReturn):
            self.update_lasti(lambda i: i - 1)
            return ExecutionResultYield(result.value)
        elif isinstance(result, ExecutionResultYield):
            return None
        else:
            assert False, result

    def execute_unpack_ex(
        self, vm: VirtualMachine, before: int, after: int
    ) -> Optional[ExecutionResult]:
        value = self.pop_value()
        elements = vm.extract_elements_as_pyobjects(value)
        min_expected = before + after

        middle = len(elements) - min_expected
        if middle < 0:
            vm.new_value_error(
                f"not enough values to unpack (expected at least {min_expected}, got {len(elements)})",
            )

        self.state.stack.extend(reversed(elements[before + middle :]))
        middle_elements = elements[before : before + middle]
        t = vm.ctx.new_list(middle_elements)
        self.push_value(t.into_pyobj(vm))
        self.state.stack.extend(reversed(elements[:before]))

        return None

    def jump(self, label: Label):
        self.update_lasti(lambda i: label.value)

    def execute_for_iter(
        self, vm: VirtualMachine, target: Label
    ) -> Optional[ExecutionResult]:
        top_of_stack = viter.PyIter.new(self.last_value(), None)
        # top_of_stack = viter.PyIter.try_from_object(vm, self.last_value())  # FIXME?

        try:
            next_obj = top_of_stack.next(vm)
        except PyImplBase:
            self.pop_value()
            raise

        if isinstance(next_obj, viter.PyIterReturnReturn):
            # TODO: del
            from vm.pyobjectrc import PyRef

            assert isinstance(next_obj.value, PyRef), (
                type(next_obj.value),
                type(top_of_stack.value._),
            )
            self.push_value(next_obj.value)
        elif isinstance(next_obj, viter.PyIterReturnStopIteration):
            self.pop_value()
            self.jump(target)
        else:
            assert False, debug_repr(next_obj.value)

    def execute_make_function(
        self, vm: VirtualMachine, flags: instruction.MakeFunctionFlags
    ) -> FrameResult:
        try:
            qualified_name = self.pop_value().downcast(pystr.PyStr)
        except PyImplError:
            raise PyImplErrorStr("expected: qualified name to be a string")
        try:
            code_obj = self.pop_value().downcast(pycode.PyCode)
        except PyImplError as e:
            print(e)
            raise PyImplErrorStr(
                "second to top value on the stack must be a code object"
            )
        if instruction.MakeFunctionFlags.CLOSURE in flags:
            closure = pytuple.PyTupleTyped.try_from_object(
                pyfunction.PyCell, vm, self.pop_value()
            )
        else:
            closure = None
        if instruction.MakeFunctionFlags.ANNOTATIONS in flags:
            annotations = self.pop_value()
        else:
            annotations = vm.ctx.new_dict().into_pyobj(vm)

        if instruction.MakeFunctionFlags.KW_ONLY_DEFAULTS in flags:
            kw_only_defaults = self.pop_value().downcast(pydict.PyDict)
            # TODO: .expect("Stack value for keyword only defaults expected to be a dict"),
        else:
            kw_only_defaults = None

        if instruction.MakeFunctionFlags.DEFAULTS in flags:
            defaults = self.pop_value().downcast(pytuple.PyTuple)
            # TODO .expect("Stack value for defaults expected to be a tuple"),
        else:
            defaults = None

        func_obj = pyfunction.PyFunction.new(
            code_obj, self.globals, closure, defaults, kw_only_defaults
        ).into_object(vm)

        func_obj.set_attr(vm.mk_str("__doc__"), vm.ctx.get_none(), vm)

        name = qualified_name._.as_str().split(".")[-1]
        func_obj.set_attr(vm.mk_str("__name__"), vm.ctx.new_str(name), vm)
        func_obj.set_attr(vm.mk_str("__qualname__"), qualified_name, vm)
        module = vm.unwrap_or_none(
            self.globals._.get_item_opt(vm.mk_str("__name__"), vm)
        )
        func_obj.set_attr(vm.mk_str("__module__"), module, vm)
        func_obj.set_attr(vm.mk_str("__annotations__"), annotations, vm)

        self.push_value(func_obj)

    def execute_binop(
        self, vm: VirtualMachine, op: instruction.BinaryOperator
    ) -> FrameResult:
        b_ref = self.pop_value()
        a_ref = self.pop_value()

        if op == instruction.BinaryOperator.Subtract:
            value = vm._sub(a_ref, b_ref)
        elif op == instruction.BinaryOperator.Add:
            value = vm._add(a_ref, b_ref)
        elif op == instruction.BinaryOperator.Multiply:
            value = vm._mul(a_ref, b_ref)
        elif op == instruction.BinaryOperator.MatrixMultiply:
            value = vm._matmul(a_ref, b_ref)
        elif op == instruction.BinaryOperator.Power:
            value = vm._pow(a_ref, b_ref)
        elif op == instruction.BinaryOperator.Divide:
            value = vm._truediv(a_ref, b_ref)
        elif op == instruction.BinaryOperator.FloorDivide:
            value = vm._floordiv(a_ref, b_ref)
        elif op == instruction.BinaryOperator.Modulo:
            value = vm._mod(a_ref, b_ref)
        elif op == instruction.BinaryOperator.Lshift:
            value = vm._lshift(a_ref, b_ref)
        elif op == instruction.BinaryOperator.Rshift:
            value = vm._rshift(a_ref, b_ref)
        elif op == instruction.BinaryOperator.Xor:
            value = vm._xor(a_ref, b_ref)
        elif op == instruction.BinaryOperator.Or:
            value = vm._or(a_ref, b_ref)
        elif op == instruction.BinaryOperator.And:
            value = vm._and(a_ref, b_ref)

        self.push_value(value)
        return None

    def execute_binop_inplace(
        self, vm: VirtualMachine, op: instruction.BinaryOperator
    ) -> FrameResult:
        b_ref = self.pop_value()
        a_ref = self.pop_value()

        if op == instruction.BinaryOperator.Subtract:
            value = vm._isub(a_ref, b_ref)
        elif op == instruction.BinaryOperator.Add:
            value = vm._iadd(a_ref, b_ref)
        elif op == instruction.BinaryOperator.Multiply:
            value = vm._imul(a_ref, b_ref)
        elif op == instruction.BinaryOperator.MatrixMultiply:
            value = vm._imatmul(a_ref, b_ref)
        elif op == instruction.BinaryOperator.Power:
            value = vm._ipow(a_ref, b_ref)
        elif op == instruction.BinaryOperator.Divide:
            value = vm._itruediv(a_ref, b_ref)
        elif op == instruction.BinaryOperator.FloorDivide:
            value = vm._ifloordiv(a_ref, b_ref)
        elif op == instruction.BinaryOperator.Modulo:
            value = vm._imod(a_ref, b_ref)
        elif op == instruction.BinaryOperator.Lshift:
            value = vm._ilshift(a_ref, b_ref)
        elif op == instruction.BinaryOperator.Rshift:
            value = vm._irshift(a_ref, b_ref)
        elif op == instruction.BinaryOperator.Xor:
            value = vm._ixor(a_ref, b_ref)
        elif op == instruction.BinaryOperator.Or:
            value = vm._ior(a_ref, b_ref)
        elif op == instruction.BinaryOperator.And:
            value = vm._iand(a_ref, b_ref)

        self.push_value(value)
        return None

    def execute_unop(
        self, vm: VirtualMachine, op: instruction.UnaryOperator
    ) -> FrameResult:
        a = self.pop_value()
        if op == instruction.UnaryOperator.Minus:
            value = vm._neg(a)
        elif op == instruction.UnaryOperator.Plus:
            value = vm._pos(a)
        elif op == instruction.UnaryOperator.Invert:
            value = vm._invert(a)
        elif op == instruction.UnaryOperator.Not:
            value = vm.ctx.new_bool(a.try_to_bool(vm)).into_pyobj(vm)
        self.push_value(value)
        return None

    def _id(self, a: PyObjectRef) -> int:
        return a.get_id()

    def _in(
        self, vm: VirtualMachine, needle: PyObjectRef, haystack: PyObjectRef
    ) -> bool:
        return vm._membership(haystack, needle).try_to_bool(vm)

    def _not_in(
        self, vm: VirtualMachine, needle: PyObjectRef, haystack: PyObjectRef
    ) -> bool:
        return not vm._membership(haystack, needle).try_to_bool(vm)

    def _is(self, a: PyObjectRef, b: PyObjectRef) -> bool:
        return a.is_(b)

    def _is_not(self, a: PyObjectRef, b: PyObjectRef) -> bool:
        return not a.is_(b)

    def execute_compare(
        self, vm: VirtualMachine, op: instruction.ComparisonOperator
    ) -> FrameResult:
        b = self.pop_value()
        a = self.pop_value()

        d = {
            instruction.ComparisonOperator.Equal: slot.PyComparisonOp.Eq,
            instruction.ComparisonOperator.NotEqual: slot.PyComparisonOp.Ne,
            instruction.ComparisonOperator.Less: slot.PyComparisonOp.Lt,
            instruction.ComparisonOperator.LessOrEqual: slot.PyComparisonOp.Le,
            instruction.ComparisonOperator.Greater: slot.PyComparisonOp.Gt,
            instruction.ComparisonOperator.GreaterOrEqual: slot.PyComparisonOp.Ge,
        }

        if op in d:
            value = a.rich_compare(b, d[op], vm)
        elif op == instruction.ComparisonOperator.Is:
            value = vm.ctx.new_bool(self._is(a, b)).into_pyobj(vm)
        elif op == instruction.ComparisonOperator.IsNot:
            value = vm.ctx.new_bool(self._is_not(a, b)).into_pyobj(vm)
        elif op == instruction.ComparisonOperator.In:
            value = vm.ctx.new_bool(self._in(vm, a, b)).into_pyobj(vm)
        elif op == instruction.ComparisonOperator.NotIn:
            value = vm.ctx.new_bool(self._not_in(vm, a, b)).into_pyobj(vm)
        elif op == instruction.ComparisonOperator.ExceptionMatch:
            value = vm.ctx.new_bool(a.is_instance(b, vm)).into_pyobj(vm)
        else:
            assert False

        self.push_value(value)
        return None


FrameResult = Optional[ExecutionResult]

FrameRef: TypeAlias = "PyRef[Frame]"
