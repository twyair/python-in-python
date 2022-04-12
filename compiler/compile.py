from __future__ import annotations
from abc import abstractmethod

import ast
import enum
from dataclasses import dataclass
from typing import Any, Callable, NoReturn, Optional, TypeVar

import bytecode.bytecode as bytecode
import bytecode.instruction as instruction
from bytecode.bytecode import (
    CodeFlags,
    CodeObject,
    ConstantData,
    ConstantDataBoolean,
    ConstantDataBytes,
    ConstantDataCode,
    ConstantDataComplex,
    ConstantDataEllipsis,
    ConstantDataFloat,
    ConstantDataInteger,
    ConstantDataNone,
    ConstantDataStr,
    ConstantDataTuple,
    ConversionFlag,
    RaiseKind,
)
from bytecode.instruction import (
    BinaryOperator,
    ComparisonOperator,
    Instruction,
    MakeFunctionFlags,
    NameIdx,
    UnaryOperator,
)
from compiler.ir import MAX_LABEL, Block, BlockIdx, CodeInfo, InstructionInfo
from compiler.symboltable import (
    Location,
    SymbolScope,
    SymbolTable,
    make_symbol_table,
    make_symbol_table_expr,
    mangle_name,
)
from indexset import IndexSet
from vm.builtins.code import PyConstant


class NameUsage(enum.Enum):
    LOAD = enum.auto()
    STORE = enum.auto()
    DELETE = enum.auto()


@dataclass
class CallType:
    # TODO: move to subclasses
    def normal_call(self) -> Instruction:
        if isinstance(self, CallTypePositional):
            return instruction.CallFunctionPositional(self.nargs)
        elif isinstance(self, CallTypeKeyword):
            return instruction.CallFunctionKeyword(self.nargs)
        elif isinstance(self, CallTypeEx):
            return instruction.CallFunctionEx(self.has_kwargs)
        else:
            assert False, self

    @abstractmethod
    def method_call(self) -> Instruction:
        ...


@dataclass
class CallTypePositional(CallType):
    nargs: int

    def method_call(self) -> Instruction:
        return instruction.CallMethodPositional(self.nargs)


@dataclass
class CallTypeKeyword(CallType):
    nargs: int

    def method_call(self) -> Instruction:
        return instruction.CallMethodKeyword(self.nargs)


@dataclass
class CallTypeEx(CallType):
    has_kwargs: bool

    def method_call(self) -> Instruction:
        return instruction.CallMethodEx(self.has_kwargs)


def is_forbidden_name(name: str) -> bool:
    return name in {"__debug__"}


class CompileErrorType(enum.Enum):
    PARSE = enum.auto()
    SYNTAX_ERROR = enum.auto()
    FUNCTION_IMPORT_STAR = enum.auto()
    INVALID_CONTINUE = enum.auto()
    INVALID_RETURN = enum.auto()
    ASYNC_RETURN_VALUE = enum.auto()
    MULTIPLE_STAR_ARGS = enum.auto()
    ASSIGN = enum.auto()
    INVALID_YIELD = enum.auto()
    INVALID_AWAIT = enum.auto()
    INVALID_YIELD_FROM = enum.auto()
    ASYNC_YIELD_FROM = enum.auto()
    INVALID_STAR_EXPR = enum.auto()
    INVALID_FUTURE_PLACEMENT = enum.auto()
    INVALID_FUTURE_FEATURE = enum.auto()
    DELETE = enum.auto()
    INVALID_BREAK = enum.auto()
    TOO_MANY_STAR_UNPACK = enum.auto()

    def get_msg(self) -> str:
        return COMPILE_ERROR_TYPE_TO_MSG[self]


COMPILE_ERROR_TYPE_TO_MSG = {
    CompileErrorType.ASSIGN: "can't assign to {}",
    CompileErrorType.DELETE: "can't delete {}",
    CompileErrorType.SYNTAX_ERROR: "{}",
    CompileErrorType.MULTIPLE_STAR_ARGS: "two starred expressions in assignment",
    CompileErrorType.INVALID_STAR_EXPR: "can't use starred expression here",
    CompileErrorType.INVALID_BREAK: "'break' outside loop",
    CompileErrorType.INVALID_CONTINUE: "'continue' outside loop",
    CompileErrorType.INVALID_RETURN: "'return' outside function",
    CompileErrorType.INVALID_YIELD: "'yield' outside function",
    CompileErrorType.INVALID_YIELD_FROM: "'yield from' outside function",
    CompileErrorType.INVALID_AWAIT: "'await' outside async function",
    CompileErrorType.ASYNC_YIELD_FROM: "'yield from' inside async function",
    CompileErrorType.ASYNC_RETURN_VALUE: "'return' with value inside async generator",
    CompileErrorType.INVALID_FUTURE_PLACEMENT: "from __future__ imports must occur at the beginning of the file",
    CompileErrorType.INVALID_FUTURE_FEATURE: "future feature {} is not defined",
    CompileErrorType.FUNCTION_IMPORT_STAR: "import * only allowed at module level",
    CompileErrorType.TOO_MANY_STAR_UNPACK: "too many expressions in star-unpacking assignment",
}


def with_compiler(
    source_path: str, opts: CompileOpts, f: Callable[[Compiler], None]
) -> CodeObject:
    compiler = Compiler.new(opts, source_path, "<module>")
    f(compiler)
    return compiler.pop_code_object()


def compile_top(ast_: ast.mod, source_path: str, opts: CompileOpts) -> CodeObject:
    if isinstance(ast_, ast.Module):
        return compile_program(ast_.body, source_path, opts)
    elif isinstance(ast_, ast.Interactive):
        return compile_program_single(ast_.body, source_path, opts)
    elif isinstance(ast_, ast.Expression):
        return compile_expression(ast_.body, source_path, opts)
    else:
        assert False, ("can't compile a FunctionType", ast_)


T_AST = TypeVar("T_AST")


def compile_impl(
    make_symbol_table: Callable[[T_AST], SymbolTable],
    compile: Callable[[Compiler, T_AST, SymbolTable], None],
) -> Callable[[T_AST, str, CompileOpts], CodeObject]:
    def inner(ast_: T_AST, source_path: str, opts: CompileOpts) -> CodeObject:
        symbol_table = make_symbol_table(ast_)
        # TODO: .into_compile_error(source_path)
        return with_compiler(
            source_path, opts, lambda compiler: compile(compiler, ast_, symbol_table)
        )

    return inner


def compile_program(
    ast_: list[ast.stmt], source_path: str, opts: CompileOpts
) -> CodeObject:
    return compile_impl(
        make_symbol_table,
        Compiler.compile_program,
    )(ast_, source_path, opts)


def compile_program_single(
    ast_: list[ast.stmt], source_path: str, opts: CompileOpts
) -> CodeObject:
    return compile_impl(
        make_symbol_table,
        Compiler.compile_program_single,
    )(ast_, source_path, opts)


def compile_expression(
    ast_: ast.expr, source_path: str, opts: CompileOpts
) -> CodeObject:
    return compile_impl(
        make_symbol_table_expr,
        Compiler.compile_eval,
    )(ast_, source_path, opts)


class CompileError(Exception):
    error: CompileErrorType
    args: tuple[Any]
    location: Optional[Location]
    source_path: str

    def __init__(self, error, args, location, source_path) -> None:
        self.error = error
        self.args = args
        self.location = location
        self.source_path = source_path

    @staticmethod
    def from_parse(e: SyntaxError, source: str, source_path: str) -> CompileError:
        return CompileError(
            CompileErrorType.SYNTAX_ERROR,
            e.args,
            # FIXME
            Location(e.lineno or 0, None, e.offset or 0, None),
            source_path,
        )

    def to_string(self) -> str:
        msg = self.error.get_msg()
        if self.args:
            msg = msg.format(self.args[0])
        return f"{msg} at {self.location}"


@dataclass
class Compiler:
    code_stack: list[CodeInfo]
    symbol_table_stack: list[SymbolTable]
    source_path: str
    current_source_location: Location
    qualified_path: list[str]
    done_with_future_stmts: bool
    future_annotations: bool
    ctx: CompileContext
    class_name: Optional[str]
    opts: CompileOpts

    @staticmethod
    def new(opts: CompileOpts, source_path: str, code_name: str) -> Compiler:
        module_code = CodeInfo(
            flags=bytecode.CodeFlags.NEW_LOCALS,
            posonlyarg_count=0,
            arg_count=0,
            kwonlyarg_count=0,
            source_path=source_path,
            first_line_number=0,
            obj_name=code_name,
            blocks=[Block()],
            current_block=instruction.Label(0),
            constants=IndexSet[ConstantData].new(),
            name_cache=IndexSet[str].new(),
            varname_cache=IndexSet[str].new(),
            cellvar_cache=IndexSet[str].new(),
            freevar_cache=IndexSet[str].new(),
        )
        return Compiler(
            code_stack=[module_code],
            symbol_table_stack=[],
            source_path=source_path,
            current_source_location=Location.default(),
            qualified_path=[],
            done_with_future_stmts=False,
            future_annotations=False,
            ctx=CompileContext(
                loop_data=None, in_class=False, func=FunctionContext.NO_FUNCTION
            ),
            class_name=None,
            opts=opts,
        )

    def error(self, error: CompileErrorType, args: tuple[Any, ...]) -> NoReturn:
        self.error_loc(error, args, self.current_source_location)

    def error_loc(
        self,
        error: CompileErrorType,
        args: tuple[Any, ...],
        location: Optional[Location],
    ) -> NoReturn:
        raise CompileError(error, args, location, self.source_path)

    def push_output(
        self,
        flags: bytecode.CodeFlags,
        posonlyarg_count: int,
        arg_count: int,
        kwonlyarg_count: int,
        obj_name: str,
    ) -> None:
        table = self.symbol_table_stack[-1].sub_tables.pop()
        cellvar_cache = IndexSet[str].from_seq(
            var for var, s in table.symbols.items() if s.scope == SymbolScope.CELL
        )
        freevar_cache = IndexSet[str].from_seq(
            var
            for var, s in table.symbols.items()
            if s.scope == SymbolScope.FREE or s.is_free_class
        )
        self.symbol_table_stack.append(table)
        info = CodeInfo(
            flags=flags,
            posonlyarg_count=posonlyarg_count,
            arg_count=arg_count,
            kwonlyarg_count=kwonlyarg_count,
            source_path=self.source_path,
            first_line_number=self.get_source_line_number(),
            obj_name=obj_name,
            blocks=[Block()],
            current_block=instruction.Label(0),
            constants=IndexSet[ConstantData].new(),
            name_cache=IndexSet[str].new(),
            varname_cache=IndexSet[str].new(),
            cellvar_cache=cellvar_cache,
            freevar_cache=freevar_cache,
        )
        self.code_stack.append(info)

    def pop_code_object(self) -> CodeObject:
        table = self.symbol_table_stack.pop()
        assert not table.sub_tables
        return self.code_stack.pop().finalize_code(self.opts.optimize)

    def name(self, name: str) -> NameIdx:
        return self._name_inner(name, lambda i: i.name_cache)

    def varname(self, name: str) -> NameIdx:
        return self._name_inner(name, lambda i: i.varname_cache)

    def _name_inner(
        self, name: str, get_cache: Callable[[CodeInfo], IndexSet[str]]
    ) -> NameIdx:
        name = self.mangle(name)
        cache = get_cache(self.current_codeinfo())
        if (r := cache.get_index_of(name)) is not None:
            return r
        return cache.insert_full(name)[0]

    def compile_program(self, body: list[ast.stmt], symbol_table: SymbolTable) -> None:
        size_before = len(self.code_stack)
        self.symbol_table_stack.append(symbol_table)

        statements, doc = get_doc(body)
        if doc is not None:
            self.emit_constant(ConstantDataStr(doc))
            self.emit(instruction.StoreGlobal(self.name("__doc__")))

        if self.find_ann(statements):
            self.emit(instruction.SetupAnnotation())

        self.compile_statements(statements)
        assert size_before == len(self.code_stack)

        self.emit_none()
        self.emit(instruction.ReturnValue())

    def compile_program_single(
        self, body: list[ast.stmt], symbol_table: SymbolTable
    ) -> None:
        self.symbol_table_stack.append(symbol_table)

        emitted_return = False
        for i, statement in enumerate(body):
            is_last = i == len(body) - 1

            if isinstance(statement, ast.Expr):
                self.compile_expression(statement.value)
                if is_last:
                    self.emit(instruction.Duplicate())
                    self.emit(instruction.PrintExpr())
                    self.emit(instruction.ReturnValue())
                    emitted_return = True
                else:
                    self.emit(instruction.PrintExpr())
            else:
                self.compile_statement(statement)

        if not emitted_return:
            self.emit_none()
            self.emit(instruction.ReturnValue())

    def compile_eval(self, expression: ast.expr, symbol_table: SymbolTable) -> None:
        self.symbol_table_stack.append(symbol_table)
        self.compile_expression(expression)
        self.emit(instruction.ReturnValue())

    def compile_statements(self, statements: list[ast.stmt]) -> None:
        for statement in statements:
            self.compile_statement(statement)

    def load_name(self, name: str) -> None:
        self.compile_name(name, NameUsage.LOAD)

    def store_name(self, name: str) -> None:
        self.compile_name(name, NameUsage.STORE)

    def mangle(self, name: str) -> str:
        return mangle_name(self.class_name, name)

    def check_forbidden_name(self, name: str, usage: NameUsage) -> None:
        if is_forbidden_name(name):
            if usage == NameUsage.STORE:
                self.error(CompileErrorType.SYNTAX_ERROR, (f"cannot assign to {name}",))
            elif usage == NameUsage.DELETE:
                self.error(CompileErrorType.SYNTAX_ERROR, (f"cannot delete {name}",))

    def compile_name(self, name: str, usage: NameUsage) -> None:
        name = self.mangle(name)
        self.check_forbidden_name(name, usage)
        symbol_table = self.symbol_table_stack[-1]
        symbol = symbol_table.lookup(name)
        assert (
            symbol is not None
        ), "The symbol must be present in the symbol table, even when it is undefined in python."
        info = self.code_stack[-1]
        cache = info.name_cache
        op_type = None
        if symbol.scope == SymbolScope.LOCAL:
            if self.ctx.in_func():
                cache = info.varname_cache
                op_type = NameOpType.FAST
            else:
                op_type = NameOpType.LOCAL
        elif symbol.scope == SymbolScope.GLOBAL_EXPLICIT:
            op_type = NameOpType.GLOBAL
        elif symbol.scope in (SymbolScope.GLOBAL_IMPLICIT, SymbolScope.UNKNOWN):
            if self.ctx.in_func():
                op_type = NameOpType.GLOBAL
            else:
                op_type = NameOpType.LOCAL
        elif symbol.scope == SymbolScope.FREE:
            cache = info.freevar_cache
            op_type = NameOpType.DEREF
        elif symbol.scope == SymbolScope.CELL:
            cache = info.cellvar_cache
            op_type = NameOpType.DEREF
        else:
            assert False, symbol

        idx = cache.get_index_of(name)
        if idx is None:
            idx = cache.insert_full(name)[0]
        if symbol.scope == SymbolScope.FREE:
            idx += len(info.cellvar_cache)

        op = None
        if op_type == NameOpType.FAST:
            if usage == NameUsage.LOAD:
                op = instruction.LoadFast
            elif usage == NameUsage.STORE:
                op = instruction.StoreFast
            elif usage == NameUsage.DELETE:
                op = instruction.DeleteFast
            else:
                assert False, usage
        elif op_type == NameOpType.GLOBAL:
            if usage == NameUsage.LOAD:
                op = instruction.LoadGlobal
            elif usage == NameUsage.STORE:
                op = instruction.StoreGlobal
            elif usage == NameUsage.DELETE:
                op = instruction.DeleteGlobal
            else:
                assert False, usage
        elif op_type == NameOpType.DEREF:
            if usage == NameUsage.LOAD:
                if not self.ctx.in_func() and self.ctx.in_class:
                    op = instruction.LoadClassDeref
                else:
                    op = instruction.LoadDeref
            elif usage == NameUsage.STORE:
                op = instruction.StoreDeref
            elif usage == NameUsage.DELETE:
                op = instruction.DeleteDeref
            else:
                assert False, usage
        elif op_type == NameOpType.LOCAL:
            if usage == NameUsage.LOAD:
                op = instruction.LoadNameAny
            elif usage == NameUsage.STORE:
                op = instruction.StoreLocal
            elif usage == NameUsage.DELETE:
                op = instruction.DeleteLocal
            else:
                assert False, usage
        else:
            assert False, op_type
        self.emit(op(idx))

    def compile_statement(self, statement: ast.stmt) -> None:
        self.set_source_location(Location.from_ast(statement))

        if isinstance(statement, ast.ImportFrom) and statement.module == "__future__":
            self.compile_future_features(statement.names)
        else:
            self.done_with_future_stmts = True

        location = Location.from_ast(statement)

        if isinstance(statement, ast.Import):
            for name in statement.names:
                self.emit_constant(ConstantDataInteger(0))
                self.emit_none()
                idx = self.name(name.name)
                self.emit(instruction.ImportName(idx))
                if name.asname is not None:
                    for part in name.name.split(".")[1:]:
                        idx = self.name(part)
                        self.emit(instruction.LoadAttr(idx))
                    self.store_name(name.asname)
                else:
                    self.store_name(name.name.split(".")[0])  # FIXME: 0 or 1?
        elif isinstance(statement, ast.ImportFrom):
            import_star = any(n.name == "*" for n in statement.names)

            from_list = None
            if import_star:
                if self.ctx.in_func():
                    self.error_loc(
                        CompileErrorType.FUNCTION_IMPORT_STAR,
                        (),
                        Location.from_ast(statement),
                    )
                from_list = (ConstantDataStr("*"),)
            else:
                from_list = tuple(ConstantDataStr(n.name) for n in statement.names)

            module_idx = None
            if statement.module is not None:
                module_idx = self.name(statement.module)

            self.emit_constant(ConstantDataInteger(statement.level))
            self.emit_constant(ConstantDataTuple(from_list))
            if module_idx is not None:
                self.emit(instruction.ImportName(module_idx))
            else:
                self.emit(instruction.ImportNameless())

            if import_star:
                self.emit(instruction.ImportStar())
            else:
                for name in statement.names:
                    idx = self.name(name.name)
                    self.emit(instruction.ImportFrom(idx))
                    if name.asname is not None:
                        self.store_name(name.asname)
                    else:
                        self.store_name(name.name)
                self.emit(instruction.Pop())
        elif isinstance(statement, ast.Expr):
            self.compile_expression(statement.value)
            self.emit(instruction.Pop())
        elif isinstance(statement, (ast.Global, ast.Nonlocal)):
            pass
        elif isinstance(statement, ast.If):
            after_block = self.new_block()
            if not statement.orelse:
                self.compile_jump_if(statement.test, False, after_block)
                self.compile_statements(statement.body)
            else:
                else_block = self.new_block()
                self.compile_jump_if(statement.test, False, else_block)
                self.compile_statements(statement.body)
                self.emit(instruction.Jump(after_block))

                self.switch_to_block(else_block)
                self.compile_statements(statement.orelse)
            self.switch_to_block(after_block)
        elif isinstance(statement, ast.While):
            self.compile_while(statement.test, statement.body, statement.orelse)
        elif isinstance(statement, ast.With):
            self.compile_with(statement.items, statement.body, False)
        elif isinstance(statement, ast.AsyncWith):
            self.compile_with(statement.items, statement.body, True)
        elif isinstance(statement, ast.For):
            self.compile_for(
                statement.target,
                statement.iter,
                statement.body,
                statement.orelse,
                False,
            )
        elif isinstance(statement, ast.AsyncFor):
            self.compile_for(
                statement.target, statement.iter, statement.body, statement.orelse, True
            )
        elif isinstance(statement, ast.Raise):
            kind = None
            if statement.exc is not None:
                self.compile_expression(statement.exc)
                if statement.cause is not None:
                    self.compile_expression(statement.cause)
                    kind = RaiseKind.RAISE_CAUSE
                else:
                    kind = RaiseKind.RAISE
            else:
                kind = RaiseKind.RERAISE
            self.emit(instruction.Raise(kind))
        elif isinstance(statement, ast.Try):
            self.compile_try_statement(
                statement.body,
                statement.handlers,
                statement.orelse,
                statement.finalbody,
            )
        elif isinstance(statement, ast.FunctionDef):
            self.compile_function_def(
                statement.name,
                statement.args,
                statement.body,
                statement.decorator_list,
                statement.returns,
                False,
            )
        elif isinstance(statement, ast.AsyncFunctionDef):
            self.compile_function_def(
                statement.name,
                statement.args,
                statement.body,
                statement.decorator_list,
                statement.returns,
                True,
            )
        elif isinstance(statement, ast.ClassDef):
            self.compile_class_def(
                statement.name,
                statement.body,
                statement.bases,
                statement.keywords,
                statement.decorator_list,
            )
        elif isinstance(statement, ast.Assert):
            if self.opts.optimize == 0:
                after_block = self.new_block()
                self.compile_jump_if(statement.test, True, after_block)

                assertion_error = self.name("AssertionError")
                self.emit(instruction.LoadGlobal(assertion_error))
                if statement.msg is not None:
                    self.compile_expression(statement.msg)
                    self.emit(instruction.CallFunctionPositional(1))
                else:
                    self.emit(instruction.CallFunctionPositional(0))
                self.emit(instruction.Raise(RaiseKind.RAISE))

                self.switch_to_block(after_block)
        elif isinstance(statement, ast.Break):
            if self.ctx.loop_data is not None:
                self.emit(instruction.Break())
            else:
                self.error_loc(CompileErrorType.INVALID_BREAK, (), location)
        elif isinstance(statement, ast.Continue):
            if self.ctx.loop_data is not None:
                self.emit(instruction.Continue(self.ctx.loop_data[0]))
            else:
                self.error_loc(CompileErrorType.INVALID_CONTINUE, (), location)
        elif isinstance(statement, ast.Return):
            if not self.ctx.in_func:
                self.error_loc(CompileErrorType.INVALID_RETURN, (), location)
            if statement.value is not None:
                if (
                    self.ctx.func == FunctionContext.ASYNC_FUNCTION
                    and CodeFlags.IS_GENERATOR in self.current_codeinfo().flags
                ):
                    self.error_loc(CompileErrorType.ASYNC_RETURN_VALUE, (), location)
                self.compile_expression(statement.value)
            else:
                self.emit_none()
            self.emit(instruction.ReturnValue())
        elif isinstance(statement, ast.Assign):
            self.compile_expression(statement.value)
            for target in statement.targets[:-1]:
                self.emit(instruction.Duplicate())
                self.compile_store(target)
            self.compile_store(statement.targets[-1])
        elif isinstance(statement, ast.AugAssign):
            self.compile_augassign(statement.target, statement.op, statement.value)
        elif isinstance(statement, ast.AnnAssign):
            self.compile_annotated_assign(
                statement.target, statement.annotation, statement.value
            )
        elif isinstance(statement, ast.Delete):
            for target in statement.targets:
                self.compile_delete(target)
        elif isinstance(statement, ast.Pass):
            pass
        else:
            assert False, statement

    def compile_delete(self, expr: ast.expr) -> None:
        if isinstance(expr, ast.Name):
            self.compile_name(expr.id, NameUsage.DELETE)
        elif isinstance(expr, ast.Attribute):
            self.check_forbidden_name(expr.attr, NameUsage.DELETE)
            self.compile_expression(expr.value)
            idx = self.name(expr.attr)
            self.emit(instruction.DeleteAttr(idx))
        elif isinstance(expr, ast.Subscript):
            self.compile_expression(expr.value)
            self.compile_expression(expr.slice)
            self.emit(instruction.DeleteSubscript())
        elif isinstance(expr, ast.Tuple):
            for element in expr.elts:
                self.compile_delete(element)
        else:
            self.error(CompileErrorType.DELETE, (expr,))

    def enter_function(self, name: str, args: ast.arguments) -> MakeFunctionFlags:
        have_defaults = bool(args.defaults)
        if have_defaults:
            size = len(args.defaults)
            for element in args.defaults:
                self.compile_expression(element)
            self.emit(instruction.BuildTuple(False, size))

        num_kw_only_defaults = 0
        for kw, default in zip(args.kwonlyargs, args.kw_defaults):
            if default is not None:
                self.emit_constant(ConstantDataStr(kw.arg))
                self.compile_expression(default)
                num_kw_only_defaults += 1
        if num_kw_only_defaults > 0:
            self.emit(instruction.BuildMap(False, False, num_kw_only_defaults))

        func_flags = MakeFunctionFlags.EMPTY
        if have_defaults:
            func_flags |= MakeFunctionFlags.DEFAULTS
        if num_kw_only_defaults > 0:
            func_flags |= MakeFunctionFlags.KW_ONLY_DEFAULTS

        self.push_output(
            CodeFlags.NEW_LOCALS | CodeFlags.IS_OPTIMIZED,
            posonlyarg_count=len(args.posonlyargs),
            arg_count=len(args.posonlyargs) + len(args.args),
            kwonlyarg_count=len(args.kwonlyargs),
            obj_name=name,
        )

        for arg in args.posonlyargs + args.args + args.kwonlyargs:
            if self.is_forbidden_arg_name(arg.arg):
                self.error(
                    CompileErrorType.SYNTAX_ERROR, (f"cannot assign to {arg.arg}",)
                )
            self.varname(arg.arg)

        def compile_varargs(va: Optional[ast.arg], flag: CodeFlags) -> None:
            if va is not None:
                self.current_codeinfo().flags |= flag
                self.varname(va.arg)

        compile_varargs(args.vararg, CodeFlags.HAS_VARARGS)
        compile_varargs(args.kwarg, CodeFlags.HAS_VARKEYWORDS)

        return func_flags

    def prepare_decorators(self, decorator_list: list[ast.expr]) -> None:
        for decorator in decorator_list:
            self.compile_expression(decorator)

    def apply_decorators(self, decorator_list: list[ast.expr]) -> None:
        for _ in decorator_list:
            self.emit(instruction.CallFunctionPositional(1))

    def compile_try_statement(
        self,
        body: list[ast.stmt],
        handlers: list[ast.ExceptHandler],
        orelse: list[ast.stmt],
        finalbody: list[ast.stmt],
    ) -> None:
        handler_block = self.new_block()
        finally_block = self.new_block()

        if finalbody:
            self.emit(instruction.SetupFinally(finally_block))

        else_block = self.new_block()

        self.emit(instruction.SetupExcept(handler_block))
        self.compile_statements(body)
        self.emit(instruction.PopBlock())
        self.emit(instruction.Jump(else_block))

        self.switch_to_block(handler_block)
        for handler in handlers:
            next_handler = self.new_block()

            if handler.type is not None:
                self.emit(instruction.Duplicate())

                self.compile_expression(handler.type)
                self.emit(
                    instruction.CompareOperation(ComparisonOperator.ExceptionMatch)
                )
                self.emit(instruction.JumpIfFalse(next_handler))

                if handler.name is not None:
                    self.store_name(handler.name)
                else:
                    self.emit(instruction.Pop())
            else:
                self.emit(instruction.Pop())

            self.compile_statements(handler.body)
            self.emit(instruction.PopException())

            if finalbody:
                self.emit(instruction.PopBlock())
                self.emit(instruction.EnterFinally())

            self.emit(instruction.Jump(finally_block))

            self.switch_to_block(next_handler)

        self.emit(instruction.Raise(RaiseKind.RERAISE))

        self.switch_to_block(else_block)
        self.compile_statements(orelse)

        if finalbody:
            self.emit(instruction.PopBlock())
            self.emit(instruction.EnterFinally())

        self.switch_to_block(finally_block)
        if finalbody:
            self.compile_statements(finalbody)
            self.emit(instruction.EndFinally())

    @staticmethod
    def is_forbidden_arg_name(name: str) -> bool:
        return is_forbidden_name(name)

    def compile_function_def(
        self,
        name: str,
        args: ast.arguments,
        body: list[ast.stmt],
        decorator_list: list[ast.expr],
        returns: Optional[ast.expr],
        is_async: bool,
    ) -> None:
        self.prepare_decorators(decorator_list)
        funcflags = self.enter_function(name, args)
        if is_async:
            self.current_codeinfo().flags |= CodeFlags.IS_COROUTINE

        prev_ctx = self.ctx

        self.ctx = CompileContext(
            loop_data=None,
            in_class=prev_ctx.in_class,
            func=FunctionContext.ASYNC_FUNCTION
            if is_async
            else FunctionContext.FUNCTION,
        )

        self.push_qualified_path(name)
        qualified_name = ".".join(self.qualified_path)
        self.push_qualified_path("<locals>")

        body, doc_str = get_doc(body)

        self.compile_statements(body)
        if not body or not isinstance(body[-1], ast.Return):
            self.emit_none()
            self.emit(instruction.ReturnValue())

        code = self.pop_code_object()
        self.qualified_path.pop()
        self.qualified_path.pop()
        self.ctx = prev_ctx

        num_annotations = 0

        if returns is not None:
            self.emit_constant(ConstantDataStr("return"))
            self.compile_annotation(returns)
            num_annotations += 1

        args_iter = args.posonlyargs + args.args + args.kwonlyargs
        if args.vararg is not None:
            args_iter.append(args.vararg)
        if args.kwarg is not None:
            args_iter.append(args.kwarg)
        for arg in args_iter:
            if arg.annotation is not None:
                self.emit_constant(ConstantDataStr(self.mangle(arg.arg)))
                self.compile_annotation(arg.annotation)
                num_annotations += 1

        if num_annotations > 0:
            funcflags |= MakeFunctionFlags.ANNOTATIONS
            self.emit(
                instruction.BuildMap(size=num_annotations, unpack=False, for_call=False)
            )

        if self.build_closure(code):
            funcflags |= MakeFunctionFlags.CLOSURE

        self.emit_constant(ConstantDataCode(code))
        self.emit_constant(ConstantDataStr(qualified_name))

        self.emit(instruction.MakeFunction(funcflags))

        self.emit(instruction.Duplicate())
        self.load_docstring(doc_str)
        self.emit(instruction.Rotate2())
        doc = self.name("__doc__")
        self.emit(instruction.StoreAttr(doc))

        self.apply_decorators(decorator_list)

        self.store_name(name)

    def build_closure(self, code: CodeObject) -> bool:
        if not code.freevars:
            return False
        for var in code.freevars:
            table = self.symbol_table_stack[-1]
            symbol = table.lookup(var)
            assert (
                symbol is not None
            ), f"couldn't look up var {var} in {code.obj_name} in {self.source_path}"
            parent_code = self.code_stack[-1]
            if symbol.scope == SymbolScope.FREE:
                vars = parent_code.freevar_cache
            elif symbol.scope == SymbolScope.CELL:
                vars = parent_code.cellvar_cache
            elif symbol.is_free_class:
                vars = parent_code.freevar_cache
            else:
                assert (
                    False
                ), f"var {var} in a {table.type} should be free or cell but it's {symbol.scope}"
            idx = vars.get_index_of(var)
            assert idx is not None
            if symbol.scope == SymbolScope.FREE:
                idx += len(parent_code.cellvar_cache)
            self.emit(instruction.LoadClosure(idx))
        self.emit(instruction.BuildTuple(False, len(code.freevars)))
        return True

    def find_ann(self, body: list[ast.stmt]) -> bool:
        for statement in body:
            if isinstance(statement, ast.AnnAssign):
                res = True
            elif isinstance(statement, (ast.For, ast.While, ast.If)):
                res = self.find_ann(statement.body) or self.find_ann(statement.orelse)
            elif isinstance(statement, ast.With):
                res = self.find_ann(statement.body)
            elif isinstance(statement, ast.Try):
                res = (
                    self.find_ann(statement.body)
                    or self.find_ann(statement.orelse)
                    or self.find_ann(statement.finalbody)
                )
            else:
                res = False
            if res:
                return True
        return False

    def compile_class_def(
        self,
        name: str,
        body: list[ast.stmt],
        bases: list[ast.expr],
        keywords: list[ast.keyword],
        decorator_list: list[ast.expr],
    ) -> None:
        self.prepare_decorators(decorator_list)

        self.emit(instruction.LoadBuildClass())

        prev_ctx = self.ctx
        self.ctx = CompileContext(
            func=FunctionContext.NO_FUNCTION, in_class=True, loop_data=None
        )

        prev_class_name = self.class_name
        self.class_name = name

        self.push_qualified_path(name)
        qualified_name = ".".join(self.qualified_path)

        self.push_output(CodeFlags.EMPTY, 0, 0, 0, name)

        new_body, doc_str = get_doc(body)

        dunder_name = self.name("__name__")
        self.emit(instruction.LoadGlobal(dunder_name))
        dunder_module = self.name("__module__")
        self.emit(instruction.StoreLocal(dunder_module))
        self.emit_constant(ConstantDataStr(qualified_name))
        qualname = self.name("__qualname__")
        self.emit(instruction.StoreLocal(qualname))
        self.load_docstring(doc_str)
        doc = self.name("__doc__")
        self.emit(instruction.StoreLocal(doc))
        if self.find_ann(body):
            self.emit(instruction.SetupAnnotation())
        self.compile_statements(new_body)

        classcell_idx = self.code_stack[-1].cellvar_cache.position(
            lambda var: var == "__class___"
        )

        if classcell_idx is not None:
            self.emit(instruction.LoadClosure(classcell_idx))
            self.emit(instruction.Duplicate())
            classcell = self.name("__classcell__")
            self.emit(instruction.StoreLocal(classcell))
        else:
            self.emit_none()

        self.emit(instruction.ReturnValue())

        code = self.pop_code_object()

        self.class_name = prev_class_name
        self.qualified_path.pop()
        self.ctx = prev_ctx

        funcflags = MakeFunctionFlags.EMPTY

        if self.build_closure(code):
            funcflags |= MakeFunctionFlags.CLOSURE

        self.emit_constant(ConstantDataCode(code))
        self.emit_constant(ConstantDataStr(name))

        self.emit(instruction.MakeFunction(funcflags))

        self.emit_constant(ConstantDataStr(qualified_name))

        call = self.compile_call_inner(2, bases, keywords)
        self.emit(call.normal_call())

        self.apply_decorators(decorator_list)

        self.store_name(name)

    def load_docstring(self, doc_str: Optional[str]) -> None:
        self.emit_constant(
            ConstantDataStr(doc_str) if doc_str is not None else ConstantDataNone()
        )

    def compile_while(
        self, test: ast.expr, body: list[ast.stmt], orelse: list[ast.stmt]
    ) -> None:
        while_block = self.new_block()
        else_block = self.new_block()
        after_block = self.new_block()

        self.emit(instruction.SetupLoop(after_block))
        self.switch_to_block(while_block)
        self.compile_jump_if(test, False, else_block)

        was_in_loop = self.ctx.loop_data
        self.ctx.loop_data = (while_block, after_block)
        self.compile_statements(body)
        self.ctx.loop_data = was_in_loop
        self.emit(instruction.Jump(while_block))
        self.switch_to_block(else_block)
        self.emit(instruction.PopBlock())
        self.compile_statements(orelse)
        self.switch_to_block(after_block)

    def compile_with(
        self, items: list[ast.withitem], body: list[ast.stmt], is_async: bool
    ) -> None:
        end_blocks = []
        for item in items:
            end_block = self.new_block()
            self.compile_expression(item.context_expr)

            if is_async:
                self.emit(instruction.BeforeAsyncWith())
                self.emit(instruction.GetAwaitable())
                self.emit_none()
                self.emit(instruction.YieldFrom())
                self.emit(instruction.SetupAsyncWith(end_block))
            else:
                self.emit(instruction.SetupWith(end_block))

            if item.optional_vars is not None:
                self.compile_store(item.optional_vars)
            else:
                self.emit(instruction.Pop())

            end_blocks.append(end_block)

        self.compile_statements(body)

        for end_block in reversed(end_blocks):
            self.emit(instruction.PopBlock())
            self.emit(instruction.EnterFinally())
            self.switch_to_block(end_block)
            self.emit(instruction.WithCleanupStart())

            if is_async:
                self.emit(instruction.GetAwaitable())
                self.emit_none()
                self.emit(instruction.YieldFrom())

            self.emit(instruction.WithCleanupFinish())

    def compile_for(
        self,
        target: ast.expr,
        iter: ast.expr,
        body: list[ast.stmt],
        orelse: list[ast.stmt],
        is_async: bool,
    ) -> None:
        for_block = self.new_block()
        else_block = self.new_block()
        after_block = self.new_block()

        self.emit(instruction.SetupLoop(after_block))

        self.compile_expression(iter)

        if is_async:
            self.emit(instruction.GetAIter())

            self.switch_to_block(for_block)
            self.emit(instruction.SetupExcept(else_block))
            self.emit(instruction.GetANext())
            self.emit_none()
            self.emit(instruction.YieldFrom())
            self.compile_store(target)
            self.emit(instruction.PopBlock())
        else:
            self.emit(instruction.GetIter())

            self.switch_to_block(for_block)
            self.emit(instruction.ForIter(else_block))

            self.compile_store(target)

        was_in_loop = self.ctx.loop_data
        self.ctx.loop_data = (for_block, after_block)
        self.compile_statements(body)
        self.ctx.loop_data = was_in_loop
        self.emit(instruction.Jump(for_block))

        self.switch_to_block(else_block)
        if is_async:
            self.emit(instruction.EndAsyncFor())
        self.emit(instruction.PopBlock())
        self.compile_statements(orelse)

        self.switch_to_block(after_block)

    def compile_chained_comparison(
        self, left: ast.expr, ops: list[ast.cmpop], vals: list[ast.expr]
    ) -> None:
        assert ops
        assert len(vals) == len(ops)
        *mid_ops, last_op = ops
        *mid_vals, last_val = vals

        def compile_cmpop(op: ast.cmpop) -> ComparisonOperator:
            if isinstance(op, ast.Eq):
                return ComparisonOperator.Equal
            elif isinstance(op, ast.NotEq):
                return ComparisonOperator.NotEqual
            elif isinstance(op, ast.Lt):
                return ComparisonOperator.Less
            elif isinstance(op, ast.LtE):
                return ComparisonOperator.LessOrEqual
            elif isinstance(op, ast.Gt):
                return ComparisonOperator.Greater
            elif isinstance(op, ast.GtE):
                return ComparisonOperator.GreaterOrEqual
            elif isinstance(op, ast.In):
                return ComparisonOperator.In
            elif isinstance(op, ast.NotIn):
                return ComparisonOperator.NotIn
            elif isinstance(op, ast.Is):
                return ComparisonOperator.Is
            elif isinstance(op, ast.IsNot):
                return ComparisonOperator.IsNot
            else:
                assert False, op

        self.compile_expression(left)

        end_blocks = None
        if mid_vals:
            end_blocks = (self.new_block(), self.new_block())

        for op, val in zip(mid_ops, mid_vals):
            self.compile_expression(val)

            self.emit(instruction.Duplicate())
            self.emit(instruction.Rotate3())

            self.emit(instruction.CompareOperation(compile_cmpop(op)))

            if end_blocks is not None:
                self.emit(instruction.JumpIfFalseOrPop(end_blocks[0]))

        self.compile_expression(last_val)
        self.emit(instruction.CompareOperation(compile_cmpop(last_op)))

        if end_blocks is not None:
            break_block, after_block = end_blocks
            self.emit(instruction.Jump(after_block))

            self.switch_to_block(break_block)
            self.emit(instruction.Rotate2())
            self.emit(instruction.Pop())

            self.switch_to_block(after_block)

    def compile_annotation(self, annotation: ast.expr) -> None:
        if self.future_annotations:
            self.emit_constant(ConstantDataStr(ast2str(annotation)))
        else:
            self.compile_expression(annotation)

    def compile_annotated_assign(
        self, target: ast.expr, annotation: ast.expr, value: Optional[ast.expr]
    ) -> None:
        if value is not None:
            self.compile_expression(value)
            self.compile_store(target)

        if self.ctx.in_func():
            return

        self.compile_annotation(annotation)

        if isinstance(target, ast.Name):
            annotations = self.name("__annotations__")
            self.emit(instruction.LoadNameAny(annotations))
            self.emit_constant(ConstantDataStr(self.mangle(target.id)))
            self.emit(instruction.StoreSubscript())
        else:
            self.emit(instruction.Pop())

    def compile_store(self, target: ast.expr) -> None:
        if isinstance(target, ast.Name):
            self.store_name(target.id)
        elif isinstance(target, ast.Subscript):
            self.compile_expression(target.value)
            self.compile_expression(target.slice)
            self.emit(instruction.StoreSubscript())
        elif isinstance(target, ast.Attribute):
            self.check_forbidden_name(target.attr, NameUsage.STORE)
            self.compile_expression(target.value)
            idx = self.name(target.attr)
            self.emit(instruction.StoreAttr(idx))
        elif isinstance(target, (ast.List, ast.Tuple)):
            seen_star = False

            for i, element in enumerate(target.elts):
                if isinstance(element, ast.Starred):
                    if seen_star:
                        self.error(CompileErrorType.MULTIPLE_STAR_ARGS, ())
                    else:
                        seen_star = True
                        before = i
                        after = len(target.elts) - i - 1
                        # TODO; check that `before` and `after` < 256
                        self.emit(instruction.UnpackEx(before=before, after=after))

            if not seen_star:
                self.emit(instruction.UnpackSequence(len(target.elts)))

            for element in target.elts:
                if isinstance(element, ast.Starred):
                    self.compile_store(element.value)
                else:
                    self.compile_store(element)
        else:
            if isinstance(target, ast.Starred):
                self.error(
                    CompileErrorType.SYNTAX_ERROR,
                    ("starred assignment target must be in a list or tuple",),
                )
            else:
                self.error(CompileErrorType.ASSIGN, (target,))

    def compile_augassign(
        self, target: ast.expr, op: ast.operator, value: ast.expr
    ) -> None:
        if isinstance(target, ast.Name):
            self.compile_name(target.id, NameUsage.LOAD)
            self.compile_expression(value)
            self.compile_op(op, True)
            self.compile_name(target.id, NameUsage.STORE)
        elif isinstance(target, ast.Subscript):
            self.compile_expression(target.value)
            self.compile_expression(target.slice)
            self.emit(instruction.Duplicate())
            self.emit(instruction.Subscript())
            self.compile_expression(value)
            self.compile_op(op, True)
            self.emit(instruction.Rotate3())
            self.emit(instruction.StoreSubscript())
        elif isinstance(target, ast.Attribute):
            self.check_forbidden_name(target.attr, NameUsage.STORE)
            self.compile_expression(target.value)
            self.emit(instruction.Duplicate())
            idx = self.name(target.attr)
            self.emit(instruction.LoadAttr(idx))
            self.compile_expression(value)
            self.compile_op(op, True)
            self.emit(instruction.Rotate2())
            self.emit(instruction.StoreAttr(idx))
        else:
            self.error(CompileErrorType.ASSIGN, (target,))

    def compile_op(self, op: ast.operator, inplace: bool):
        if isinstance(op, ast.Add):
            bop = BinaryOperator.Add
        elif isinstance(op, ast.Sub):
            bop = BinaryOperator.Subtract
        elif isinstance(op, ast.Mult):
            bop = BinaryOperator.Multiply
        elif isinstance(op, ast.MatMult):
            bop = BinaryOperator.MatrixMultiply
        elif isinstance(op, ast.Div):
            bop = BinaryOperator.Divide
        elif isinstance(op, ast.FloorDiv):
            bop = BinaryOperator.FloorDivide
        elif isinstance(op, ast.Mod):
            bop = BinaryOperator.Modulo
        elif isinstance(op, ast.Pow):
            bop = BinaryOperator.Power
        elif isinstance(op, ast.LShift):
            bop = BinaryOperator.Lshift
        elif isinstance(op, ast.RShift):
            bop = BinaryOperator.Rshift
        elif isinstance(op, ast.BitOr):
            bop = BinaryOperator.Or
        elif isinstance(op, ast.BitXor):
            bop = BinaryOperator.Xor
        elif isinstance(op, ast.BitAnd):
            bop = BinaryOperator.And
        else:
            assert False, op
        if inplace:
            self.emit(instruction.BinaryOperationInplace(bop))
        else:
            self.emit(instruction.BinaryOperation(bop))

    def compile_jump_if(
        self, expression: ast.expr, condition: bool, target_block: BlockIdx
    ) -> None:
        if isinstance(expression, ast.BoolOp):
            if isinstance(expression.op, ast.And):
                if condition:
                    end_block = self.new_block()
                    last_value, values = expression.values[-1], expression.values[:-1]
                    for value in values:
                        self.compile_jump_if(value, False, end_block)
                    self.compile_jump_if(last_value, True, target_block)
                    self.switch_to_block(end_block)
                else:
                    for value in expression.values:
                        self.compile_jump_if(value, False, target_block)
            elif isinstance(expression.op, ast.Or):
                if condition:
                    for value in expression.values:
                        self.compile_jump_if(value, True, target_block)
                else:
                    end_block = self.new_block()
                    last_value, values = expression.values[-1], expression.values[:-1]
                    for value in values:
                        self.compile_jump_if(value, True, end_block)
                    self.compile_jump_if(last_value, False, target_block)
                    self.switch_to_block(end_block)
        elif isinstance(expression, ast.UnaryOp) and isinstance(expression.op, ast.Not):
            self.compile_jump_if(expression.operand, not condition, target_block)
        else:
            self.compile_expression(expression)
            if condition:
                self.emit(instruction.JumpIfTrue(target_block))
            else:
                self.emit(instruction.JumpIfFalse(target_block))

    def compile_bool_op(self, op: ast.boolop, values: list[ast.expr]) -> None:
        after_block = self.new_block()
        *values, last_value = values
        for value in values:
            self.compile_expression(value)
            if isinstance(op, ast.And):
                self.emit(instruction.JumpIfFalseOrPop(after_block))
            elif isinstance(op, ast.Or):
                self.emit(instruction.JumpIfTrueOrPop(after_block))
        self.compile_expression(last_value)
        self.switch_to_block(after_block)

    def compile_dict(
        self, keys: list[Optional[ast.expr]], values: list[ast.expr]
    ) -> None:
        size = 0

        values_t = []
        pairs_f = []
        for key, value in zip(keys, values):
            if key is None:
                values_t.append(value)
            else:
                pairs_f.append((key, value))

        if pairs_f:
            subsize = 0
            for key, value in pairs_f:
                assert key is not None
                self.compile_expression(key)
                self.compile_expression(value)
                subsize += 1
            self.emit(instruction.BuildMap(size=subsize, unpack=False, for_call=False))
            size += 1

        has_unpacking = bool(values_t)
        for value in values_t:
            self.compile_expression(value)
            size += 1

        if size == 0:
            self.emit(instruction.BuildMap(size=size, unpack=False, for_call=False))
        if size > 1 or has_unpacking:
            self.emit(instruction.BuildMap(size=size, unpack=True, for_call=False))

    def compile_expression(self, expr: ast.expr) -> None:
        self.set_source_location(Location.from_ast(expr))

        if isinstance(expr, ast.Call):
            self.compile_call(expr.func, expr.args, expr.keywords)
        elif isinstance(expr, ast.BoolOp):
            self.compile_bool_op(expr.op, expr.values)
        elif isinstance(expr, ast.BinOp):
            self.compile_expression(expr.left)
            self.compile_expression(expr.right)
            self.compile_op(expr.op, False)
        elif isinstance(expr, ast.Subscript):
            self.compile_expression(expr.value)
            self.compile_expression(expr.slice)
            self.emit(instruction.Subscript())
        elif isinstance(expr, ast.UnaryOp):
            self.compile_expression(expr.operand)

            if isinstance(expr.op, ast.UAdd):
                op = UnaryOperator.Plus
            elif isinstance(expr.op, ast.USub):
                op = UnaryOperator.Minus
            elif isinstance(expr.op, ast.Not):
                op = UnaryOperator.Not
            elif isinstance(expr.op, ast.Invert):
                op = UnaryOperator.Invert
            else:
                assert False, expr.op

            self.emit(instruction.UnaryOperation(op))
        elif isinstance(expr, ast.Attribute):
            self.compile_expression(expr.value)
            idx = self.name(expr.attr)
            self.emit(instruction.LoadAttr(idx))
        elif isinstance(expr, ast.Compare):
            self.compile_chained_comparison(expr.left, expr.ops, expr.comparators)
        elif isinstance(expr, ast.Constant):
            self.emit_constant(compile_constant(expr))
        elif isinstance(expr, ast.List):
            size, unpack = self.gather_elements(0, expr.elts)
            self.emit(instruction.BuildList(unpack, size))
        elif isinstance(expr, ast.Tuple):
            size, unpack = self.gather_elements(0, expr.elts)
            self.emit(instruction.BuildTuple(unpack, size))
        elif isinstance(expr, ast.Set):
            size, unpack = self.gather_elements(0, expr.elts)
            self.emit(instruction.BuildSet(unpack, size))
        elif isinstance(expr, ast.Dict):
            self.compile_dict(expr.keys, expr.values)
        elif isinstance(expr, ast.Slice):

            def compile_bound(bound: Optional[ast.expr]) -> None:
                if bound is not None:
                    self.compile_expression(bound)
                else:
                    self.emit_none()

            compile_bound(expr.lower)
            compile_bound(expr.upper)
            if expr.step is not None:
                self.compile_expression(expr.step)
            self.emit(instruction.BuildSlice(expr.step is not None))
        elif isinstance(expr, ast.Yield):
            if not self.ctx.in_func():
                self.error(CompileErrorType.INVALID_YIELD, ())
            self.mark_generator()
            if expr.value is not None:
                self.compile_expression(expr.value)
            else:
                self.emit_none()
            self.emit(instruction.YieldValue())
        elif isinstance(expr, ast.Await):
            if self.ctx.func != FunctionContext.ASYNC_FUNCTION:
                self.error(CompileErrorType.INVALID_AWAIT, ())
            self.compile_expression(expr.value)
            self.emit(instruction.GetAwaitable())
            self.emit_none()
            self.emit(instruction.YieldFrom())
        elif isinstance(expr, ast.YieldFrom):
            if self.ctx.func == FunctionContext.NO_FUNCTION:
                self.error(CompileErrorType.INVALID_YIELD_FROM, ())
            elif self.ctx.func == FunctionContext.ASYNC_FUNCTION:
                self.error(CompileErrorType.ASYNC_YIELD_FROM, ())
            self.mark_generator()
            self.compile_expression(expr.value)
            self.emit(instruction.GetIter())
            self.emit_none()
            self.emit(instruction.YieldFrom())
        elif isinstance(expr, ast.JoinedStr):
            if (value := try_get_constant_string(expr.values)) is not None:
                self.emit_constant(ConstantDataStr(value))
            else:
                for value in expr.values:
                    self.compile_expression(value)
                self.emit(instruction.BuildString(len(expr.values)))
        elif isinstance(expr, ast.FormattedValue):
            if expr.format_spec is not None:
                self.compile_expression(expr.format_spec)
            else:
                self.emit_constant(ConstantDataStr(""))
            self.compile_expression(expr.value)
            self.emit(instruction.FormatValue(compile_conversion_flag(expr.conversion)))
        elif isinstance(expr, ast.Name):
            self.load_name(expr.id)
        elif isinstance(expr, ast.Lambda):
            prev_ctx = self.ctx
            self.ctx = CompileContext(
                loop_data=None,
                in_class=prev_ctx.in_class,
                func=FunctionContext.FUNCTION,
            )

            name = "<lambda>"
            funcflags = self.enter_function(name, expr.args)
            self.compile_expression(expr.body)
            self.emit(instruction.ReturnValue())
            code = self.pop_code_object()
            if self.build_closure(code):
                funcflags |= MakeFunctionFlags.CLOSURE
            self.emit_constant(ConstantDataCode(code))
            self.emit_constant(ConstantDataStr(name))
            self.emit(instruction.MakeFunction(funcflags))

            self.ctx = prev_ctx
        elif isinstance(expr, ast.ListComp):
            self.compile_comprehension(
                "<listcomp>",
                instruction.BuildList(False, 0),
                expr.generators,
                lambda compiler: ignore(
                    compiler.compile_comprehension_element(expr.elt),
                    compiler.emit(instruction.ListAppend(1 + len(expr.generators))),
                ),
            )
        elif isinstance(expr, ast.SetComp):
            self.compile_comprehension(
                "<listcomp>",
                instruction.BuildSet(False, 0),
                expr.generators,
                lambda compiler: ignore(
                    compiler.compile_comprehension_element(expr.elt),
                    compiler.emit(instruction.SetAdd(1 + len(expr.generators))),
                ),
            )
        elif isinstance(expr, ast.DictComp):
            self.compile_comprehension(
                "<dictcomp>",
                instruction.BuildMap(size=0, for_call=False, unpack=False),
                expr.generators,
                lambda compiler: ignore(
                    compiler.compile_expression(expr.key),
                    compiler.compile_expression(expr.value),
                    compiler.emit(instruction.MapAddRev(1 + len(expr.generators))),
                ),
            )
        elif isinstance(expr, ast.GeneratorExp):
            self.compile_comprehension(
                "<genexpr>",
                None,
                expr.generators,
                lambda compiler: ignore(
                    compiler.compile_comprehension_element(expr.elt),
                    compiler.mark_generator(),
                    compiler.emit(instruction.YieldValue()),
                    compiler.emit(instruction.Pop()),
                ),
            )
        elif isinstance(expr, ast.Starred):
            self.error(CompileErrorType.INVALID_STAR_EXPR, ())
        elif isinstance(expr, ast.IfExp):
            else_block = self.new_block()
            after_block = self.new_block()
            self.compile_jump_if(expr.test, False, else_block)

            self.compile_expression(expr.body)
            self.emit(instruction.Jump(after_block))

            self.switch_to_block(else_block)
            self.compile_expression(expr.orelse)

            self.switch_to_block(after_block)
        elif isinstance(expr, ast.NamedExpr):
            self.compile_expression(expr.value)
            self.emit(instruction.Duplicate())
            self.compile_store(expr.target)
        else:
            assert False, expr

    def compile_keywords(self, keywords: list[ast.keyword]) -> None:
        size = 0
        group_0 = [k for k in keywords if k.arg is None]
        group_1 = [k for k in keywords if k.arg is not None]
        for keyword in group_0:
            self.compile_expression(keyword.value)
            size += 1
        if group_1:
            subsize = len(group_1)
            for keyword in group_1:
                assert keyword.arg is not None
                self.emit_constant(ConstantDataStr(keyword.arg))
                self.compile_expression(keyword.value)
            self.emit(instruction.BuildMap(size=subsize, unpack=False, for_call=False))
            size += 1
        if size > 1:
            self.emit(instruction.BuildMap(size=size, unpack=True, for_call=True))

    def compile_call(
        self, func: ast.expr, args: list[ast.expr], keywords: list[ast.keyword]
    ) -> None:
        if isinstance(func, ast.Attribute):
            self.compile_expression(func.value)
            idx = self.name(func.attr)
            self.emit(instruction.LoadMethod(idx))
            method = True
        else:
            self.compile_expression(func)
            method = False

        call = self.compile_call_inner(0, args, keywords)
        if method:
            self.emit(call.method_call())
        else:
            self.emit(call.normal_call())

    def compile_call_inner(
        self,
        additional_positional: int,
        args: list[ast.expr],
        keywords: list[ast.keyword],
    ) -> CallType:
        count = len(args) + len(keywords) + additional_positional

        size, unpack = self.gather_elements(additional_positional, args)
        has_double_star = any(k is None for k in keywords)

        for keyword in keywords:
            if keyword.arg is not None:
                self.check_forbidden_name(keyword.arg, NameUsage.STORE)

        if unpack or has_double_star:
            self.emit(instruction.BuildTuple(size=size, unpack=unpack))

            has_kwargs = bool(keywords)
            if has_kwargs:
                self.compile_keywords(keywords)
            call = CallTypeEx(has_kwargs)
        elif keywords:
            kwarg_names = []
            for keyword in keywords:
                if keyword.arg is not None:
                    kwarg_names.append(ConstantDataStr(keyword.arg))
                else:
                    assert False, "name must be set"
                self.compile_expression(keyword.value)
            self.emit_constant(ConstantDataTuple(tuple(kwarg_names)))
            call = CallTypeKeyword(count)
        else:
            call = CallTypePositional(count)
        return call

    def gather_elements(
        self, before: int, elements: list[ast.expr]
    ) -> tuple[int, bool]:
        has_stars = any(isinstance(e, ast.Starred) for e in elements)

        if has_stars:
            size = 0
            if before > 0:
                self.emit(instruction.BuildTuple(size=before, unpack=False))
                size += 1

            group = []
            starred_group = []
            for element in elements:
                if isinstance(element, ast.Starred):
                    starred_group.append(element.value)
                else:
                    group.append(element)

            for starred, run in [(False, group), (True, starred_group)]:
                run_size = len(run)
                for value in run:
                    self.compile_expression(value)
                if starred:
                    size += run_size
                else:
                    self.emit(instruction.BuildTuple(size=run_size, unpack=False))
        else:
            for element in elements:
                self.compile_expression(element)
            size = before + len(elements)
        return size, has_stars

    def compile_comprehension_element(self, element: ast.expr) -> None:
        try:
            self.compile_expression(element)
        except CompileError as exc:
            if exc.error == CompileErrorType.INVALID_STAR_EXPR:
                self.error(
                    CompileErrorType.SYNTAX_ERROR,
                    ("iterable unpacking cannot be used in comprehension",),
                )
            raise

    def compile_comprehension(
        self,
        name: str,
        init_collection: Optional[Instruction],
        generators: list[ast.comprehension],
        compile_element: Callable[[Compiler], None],
    ) -> None:
        prev_ctx = self.ctx

        self.ctx = CompileContext(
            loop_data=None,
            in_class=prev_ctx.in_class,
            func=FunctionContext.FUNCTION,
        )

        assert not generators

        self.push_output(CodeFlags.NEW_LOCALS | CodeFlags.IS_OPTIMIZED, 1, 1, 0, name)

        arg0 = self.varname(".0")

        return_none = init_collection is None
        if init_collection is not None:
            self.emit(init_collection)

        loop_labels = []
        for generator in generators:
            if generator.is_async:
                raise NotImplementedError("async for comprehensions")

            loop_block = self.new_block()
            after_block = self.new_block()

            self.emit(instruction.SetupLoop(after_block))

            if not loop_labels:
                self.emit(instruction.LoadFast(arg0))
            else:
                self.compile_expression(generator.iter)

                self.emit(instruction.GetIter())
            loop_labels.append((loop_block, after_block))

            self.switch_to_block(loop_block)
            self.emit(instruction.ForIter(after_block))

            self.compile_store(generator.target)

            for if_condition in generator.ifs:
                self.compile_jump_if(if_condition, False, loop_block)

        compile_element(self)

        for loop_block, after_block in reversed(loop_labels):
            self.emit(instruction.Jump(loop_block))

            self.switch_to_block(after_block)
            self.emit(instruction.PopBlock())

        if return_none:
            self.emit_none()

        self.emit(instruction.ReturnValue())

        code = self.pop_code_object()

        self.ctx = prev_ctx

        funcflags = MakeFunctionFlags.EMPTY
        if self.build_closure(code):
            funcflags |= MakeFunctionFlags.CLOSURE

        self.emit_constant(ConstantDataCode(code))

        self.emit_constant(ConstantDataStr(name))

        self.emit(instruction.MakeFunction(funcflags))

        self.compile_expression(generators[0].iter)

        self.emit(instruction.GetIter())

        self.emit(instruction.CallFunctionPositional(1))

    def compile_future_features(self, features: list[ast.alias]) -> None:
        if self.done_with_future_stmts:
            self.error(CompileErrorType.INVALID_FUTURE_PLACEMENT, ())
        for feature in features:
            if feature == "annotations":
                pass
            elif feature not in {
                "nested_scopes",
                "generators",
                "division",
                "absolute_import",
                "with_statement",
                "print_function",
                "unicode_literals",
            }:
                self.error(CompileErrorType.INVALID_FUTURE_FEATURE, (feature,))

    def emit(self, instr: Instruction) -> None:
        location = compile_location(self.current_source_location)
        self.current_block().instructions.append(InstructionInfo(instr, location))

    def emit_constant(self, constant: ConstantData) -> None:
        info = self.current_codeinfo()
        idx = info.constants.insert_full(PyConstant(constant))[0]
        self.emit(instruction.LoadConst(idx))

    def emit_none(self) -> None:
        self.emit_constant(ConstantDataNone())

    def current_codeinfo(self) -> CodeInfo:
        return self.code_stack[-1]

    def current_block(self) -> Block:
        info = self.current_codeinfo()
        return info.blocks[info.current_block.value]

    def new_block(self) -> BlockIdx:
        code = self.current_codeinfo()
        idx = instruction.Label(len(code.blocks))
        code.blocks.append(Block())
        return idx

    def switch_to_block(self, block: BlockIdx) -> None:
        code = self.current_codeinfo()
        prev = code.current_block
        assert code.blocks[block.value].next == MAX_LABEL
        prev_block = code.blocks[prev.value]
        assert prev_block.next == MAX_LABEL
        prev_block.next = block
        code.current_block = block

    def set_source_location(self, location: Location) -> None:
        self.current_source_location = location

    def get_source_line_number(self) -> int:
        return self.current_source_location.row()

    def push_qualified_path(self, name: str) -> None:
        self.qualified_path.append(name)

    def mark_generator(self) -> None:
        self.current_codeinfo().flags |= CodeFlags.IS_GENERATOR


class NameOpType(enum.Enum):
    FAST = enum.auto()
    GLOBAL = enum.auto()
    DEREF = enum.auto()
    LOCAL = enum.auto()


@dataclass
class CompileOpts:
    optimize: int


@dataclass
class CompileContext:
    loop_data: Optional[tuple[BlockIdx, BlockIdx]]
    in_class: bool
    func: FunctionContext

    def in_func(self) -> bool:
        return self.func != FunctionContext.NO_FUNCTION


class FunctionContext(enum.Enum):
    NO_FUNCTION = enum.auto()
    FUNCTION = enum.auto()
    ASYNC_FUNCTION = enum.auto()


def get_doc(body: list[ast.stmt]) -> tuple[list[ast.stmt], Optional[str]]:
    if body:
        val = body[0]
        if isinstance(val, ast.Expr):
            doc = try_get_constant_string([val.value])
            if doc is not None:
                return (body[1:], doc)
    return (body, None)


def try_get_constant_string(values: list[ast.expr]) -> Optional[str]:
    out_string = ""
    values = list(reversed(values))
    while values:
        value = values.pop()
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            out_string += value.value
        elif isinstance(value, ast.JoinedStr):
            values.extend(reversed(value.values))
        else:
            return None
    return out_string


def ignore(*args: Any) -> None:
    pass


def compile_location(location: Optional[Location]) -> Optional[Location]:
    return location


def compile_conversion_flag(c: Optional[int]) -> ConversionFlag:
    # FIXME!
    return {
        None: ConversionFlag.NONE,
        0: ConversionFlag.STR,
        1: ConversionFlag.REPR,
        2: ConversionFlag.ASCII,
    }[c]


def compile_constant(value: ast.Constant) -> ConstantData:
    value = value.value
    if value is None:
        return ConstantDataNone()
    if value is ...:
        return ConstantDataEllipsis()
    elif isinstance(value, bool):
        return ConstantDataBoolean(value)
    elif isinstance(value, int):
        return ConstantDataInteger(value)
    elif isinstance(value, float):
        return ConstantDataFloat(value)
    elif isinstance(value, complex):
        return ConstantDataComplex(value)
    elif isinstance(value, str):
        return ConstantDataStr(value)
    elif isinstance(value, bytes):
        return ConstantDataBytes(value)
    elif isinstance(value, tuple):
        return ConstantDataTuple(tuple(compile_constant(c) for c in value))
    else:
        assert False, value


def ast2str(a: ast.AST) -> str:
    return ast.unparse(a)


def test_compile_exec(source: str) -> CodeObject:
    compiler = Compiler.new(CompileOpts(0), "source_path", "<module>")
    body = ast.parse(source).body
    symbol_scope = make_symbol_table(body)
    compiler.compile_program(body, symbol_scope)
    return compiler.pop_code_object()
