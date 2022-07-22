from __future__ import annotations
import ast
from copy import copy
from dataclasses import dataclass, field
import dataclasses
from typing import Dict, Optional
import enum


# based on [https://github.com/RustPython/RustPython/blob/main/compiler/src/symboltable.rs]


@dataclass
class Location:
    lineno: int
    end_lineno: Optional[int]
    col_offset: int
    end_col_offset: Optional[int]

    @staticmethod
    def from_ast(a: ast.AST, /) -> Location:
        return Location(
            lineno=0,  # a.lineno,
            end_lineno=0,  # a.end_lineno,
            col_offset=0,  # a.col_offset,
            end_col_offset=0,  # a.end_col_offset,
        )

    @staticmethod
    def default() -> Location:
        return Location(-1, None, -1, None)

    def row(self) -> int:
        return self.lineno

    def __str__(self) -> str:
        return f"line {self.lineno} column {self.col_offset}"


class SymbolTableType(enum.Enum):
    MODULE = enum.auto()
    CLASS = enum.auto()
    FUNCTION = enum.auto()
    COMPREHENSION = enum.auto()

    def __str__(self) -> str:
        return self.name.lower()


class SymbolScope(enum.Enum):
    UNKNOWN = enum.auto()
    LOCAL = enum.auto()
    GLOBAL_EXPLICIT = enum.auto()
    GLOBAL_IMPLICIT = enum.auto()
    FREE = enum.auto()
    CELL = enum.auto()


@dataclass
class Symbol:
    name: str
    scope: SymbolScope = SymbolScope.UNKNOWN
    is_referenced: bool = False
    is_assigned: bool = False
    is_parameter: bool = False
    is_annotated: bool = False
    is_imported: bool = False
    is_nonlocal: bool = False
    is_assign_namedexpr_in_comprehension: bool = False
    is_iter: bool = False
    is_free_class: bool = False

    def is_global(self) -> bool:
        return self.scope in (SymbolScope.GLOBAL_EXPLICIT, SymbolScope.GLOBAL_IMPLICIT)

    def is_local(self) -> bool:
        return self.scope == SymbolScope.LOCAL

    def is_bound(self) -> bool:
        return self.is_assigned or self.is_parameter or self.is_imported or self.is_iter

    def clone(self) -> Symbol:
        return copy(self)


@dataclass
class SymbolTableError(Exception):
    error: str
    location: Optional[Location]


@dataclass
class SymbolTable:
    name: str
    type: SymbolTableType
    line_number: int
    is_nested: bool
    symbols: dict[str, Symbol] = field(default_factory=dict)
    sub_tables: list[SymbolTable] = field(default_factory=list)

    def lookup(self, name: str) -> Optional[Symbol]:
        return self.symbols.get(name)


def analyze_symbol_table(symbol_table: SymbolTable) -> None:
    analyzer = SymbolTableAnalyzer([])
    analyzer.analyze_symbol_table(symbol_table)


SymbolMap = Dict[str, Symbol]


@dataclass
class SymbolTableAnalyzer:
    tables: list[tuple[SymbolMap, SymbolTableType]]

    def analyze_symbol_table(self, symbol_table: SymbolTable) -> None:
        info = (symbol_table.symbols, symbol_table.type)

        self.tables.append(info)
        try:
            for sub_table in symbol_table.sub_tables:
                self.analyze_symbol_table(sub_table)
        except SymbolTableError:
            raise
        finally:
            self.tables.pop()

        for symbol in symbol_table.symbols.values():
            self.analyze_symbol(symbol, symbol_table.type, symbol_table.sub_tables)

    def analyze_symbol(
        self, symbol: Symbol, st_type: SymbolTableType, sub_tables: list[SymbolTable]
    ) -> None:
        if (
            symbol.is_assign_namedexpr_in_comprehension
            and st_type == SymbolTableType.COMPREHENSION
        ):
            return self.analyze_symbol_comprehension(symbol, 0)
        elif symbol.scope == SymbolScope.FREE:
            if self.tables:
                scope_depth = len(self.tables)
                if (
                    scope_depth < 2
                    or self.found_in_outer_scope(symbol.name) != SymbolScope.FREE
                ):
                    # assert False, (
                    #     scope_depth,
                    #     self.found_in_outer_scope(symbol.name),
                    #     symbol,
                    # )
                    raise SymbolTableError(
                        f"no binding for nonlocal '{symbol.name}' found", None
                    )
            else:
                raise SymbolTableError(
                    f"nonlocal {symbol.name} defined at place without an enclosing scope",
                    None,
                )
        elif symbol.scope in (SymbolScope.GLOBAL_EXPLICIT, SymbolScope.GLOBAL_IMPLICIT):
            pass
        elif symbol.scope in (SymbolScope.LOCAL, SymbolScope.CELL):
            pass
        elif symbol.scope == SymbolScope.UNKNOWN:
            if symbol.is_bound():
                symbol.scope = (
                    self.found_in_inner_scope(sub_tables, symbol.name, st_type)
                    or SymbolScope.LOCAL
                )
            elif (scope := self.found_in_outer_scope(symbol.name)) is not None:
                symbol.scope = scope
            elif not self.tables:
                pass
            else:
                symbol.scope = SymbolScope.GLOBAL_IMPLICIT

    def found_in_outer_scope(self, name: str) -> Optional[SymbolScope]:
        decl_depth: Optional[int] = None
        for i, (symbols, type) in enumerate(reversed(self.tables)):
            if (
                type == SymbolTableType.MODULE
                or type == SymbolTableType.CLASS
                and name != "__class__"
            ):
                continue
            if (sym := symbols.get(name)) is not None:
                if sym.scope == SymbolScope.GLOBAL_EXPLICIT:
                    return SymbolScope.GLOBAL_EXPLICIT
                elif sym.scope == SymbolScope.GLOBAL_IMPLICIT:
                    pass
                else:
                    if sym.is_bound():
                        decl_depth = i
                        break

        if decl_depth is None:
            return None

        if decl_depth > 0:
            for (table, type) in reversed(self.tables[-decl_depth:]):
                if type == SymbolTableType.CLASS:
                    if (free_class := table.get(name)) is not None:
                        free_class.is_free_class = True
                    else:
                        symbol = Symbol(
                            name, is_free_class=True, scope=SymbolScope.FREE
                        )
                        table[name] = symbol
                        # assert False, (symbol, self.tables)
                elif name not in table:
                    symbol = Symbol(name, scope=SymbolScope.FREE)
                    table[name] = symbol
                    # assert False, (name, decl_depth, [d.keys() for d, _ in self.tables])

        return SymbolScope.FREE

    def found_in_inner_scope(
        self, sub_tables: list[SymbolTable], name: str, st_type: SymbolTableType
    ) -> Optional[SymbolScope]:
        for st in sub_tables:
            if (sym := st.lookup(name)) is not None:
                if sym.scope == SymbolScope.FREE or sym.is_free_class:
                    if not (st_type == SymbolTableType.CLASS and name != "__class__"):
                        return SymbolScope.CELL
                elif sym.scope == SymbolScope.GLOBAL_EXPLICIT and not self.tables:
                    return SymbolScope.GLOBAL_EXPLICIT
        return None

    def analyze_symbol_comprehension(self, symbol: Symbol, parent_offset: int) -> None:
        symbols, table_type = self.tables[-parent_offset - 1]

        if symbol.is_iter:
            raise SymbolTableError(
                f"assignment expression cannot rebind comprehension iteration variable {symbol.name}",
                Location.default(),
            )

        if table_type == SymbolTableType.MODULE:
            symbol.scope = SymbolScope.GLOBAL_IMPLICIT
        elif table_type == SymbolTableType.CLASS:
            raise SymbolTableError(
                "assignment expression within a comprehension cannot be used in a class body",
                Location.default(),
            )
        elif table_type == SymbolTableType.FUNCTION:
            if (parent_symbol := symbols.get(symbol.name)) is not None:
                if parent_symbol.scope == SymbolScope.UNKNOWN:
                    parent_symbol.is_assigned = True

                if parent_symbol.is_global():
                    symbol.scope = parent_symbol.scope
                else:
                    symbol.scope = SymbolScope.FREE
            else:
                cloned_sym = symbol.clone()
                cloned_sym.scope = SymbolScope.LOCAL
                symbols[cloned_sym.name] = cloned_sym

        elif table_type == SymbolTableType.COMPREHENSION:
            if (parent_symbol := symbols.get(symbol.name)) is not None:
                if parent_symbol.is_iter:
                    raise SymbolTableError(
                        f"assignment expression cannot rebind comprehension iteration variable {symbol.name}",
                        Location.default(),
                    )
                parent_symbol.is_assigned = True
            else:
                cloned_sym = symbol.clone()
                cloned_sym.scope = SymbolScope.FREE
                symbols[cloned_sym.name] = cloned_sym

            self.analyze_symbol_comprehension(symbol, parent_offset + 1)


class SymbolUsage(enum.Enum):
    GLOBAL = enum.auto()
    NONLOCAL = enum.auto()
    USED = enum.auto()
    ASSIGNED = enum.auto()
    IMPORTED = enum.auto()
    ANNOTATION_ASSIGNED = enum.auto()
    PARAMETER = enum.auto()
    ANNOTATION_PARAMETER = enum.auto()
    ASSIGNED_NAMED_EXPR_IN_COMPR = enum.auto()
    ITER = enum.auto()


class ExpressionContext(enum.Enum):
    LOAD = enum.auto()
    STORE = enum.auto()
    DELETE = enum.auto()
    ITER = enum.auto()
    ITER_DEFINITION_EXP = enum.auto()


@dataclass
class SymbolTableBuilder:
    class_name: Optional[str]
    tables: list[SymbolTable]
    future_annotations: bool

    @staticmethod
    def new() -> SymbolTableBuilder:
        this = SymbolTableBuilder(None, [], False)
        this.enter_scope("top", SymbolTableType.MODULE, 0)
        return this

    def finish(self) -> SymbolTable:
        assert len(self.tables) == 1, len(self.tables)
        symbol_table = self.tables.pop()
        analyze_symbol_table(symbol_table)
        return symbol_table

    def enter_scope(self, name: str, type: SymbolTableType, line_number: int) -> None:
        is_nested = False
        if self.tables and (
            self.tables[-1].is_nested
            or self.tables[-1].type == SymbolTableType.FUNCTION
        ):
            is_nested = True
        table = SymbolTable(name, type, line_number, is_nested)
        self.tables.append(table)

    def leave_scope(self):
        table = self.tables.pop()
        self.tables[-1].sub_tables.append(table)

    def scan_statements(self, statements: list[ast.stmt]) -> None:
        for statement in statements:
            self.scan_statement(statement)

    def scan_parameters(self, parameters: list[ast.arg]) -> None:
        for parameter in parameters:
            self.scan_parameter(parameter)

    def scan_parameter(self, parameter: ast.arg) -> None:
        usage = (
            SymbolUsage.ANNOTATION_PARAMETER
            if parameter.annotation is not None
            else SymbolUsage.PARAMETER
        )
        self.register_name(parameter.arg, usage, Location.from_ast(parameter))

    def scan_parameters_annotations(self, parameters: list[ast.arg]) -> None:
        for parameter in parameters:
            self.scan_parameter_annotation(parameter)

    def scan_parameter_annotation(self, parameter: ast.arg) -> None:
        if parameter.annotation is not None:
            self.scan_annotation(parameter.annotation)

    def scan_annotation(self, annotation: ast.expr) -> None:
        if not self.future_annotations:
            self.scan_expression(annotation, ExpressionContext.LOAD)

    def scan_statement(self, statement: ast.stmt) -> None:
        location = Location.from_ast(statement)
        if isinstance(statement, ast.ImportFrom):
            if statement.module == "__future__":
                for feature in statement.names:
                    if feature.name == "annotations":
                        self.future_annotations = True
        if isinstance(statement, ast.Global):
            for name in statement.names:
                self.register_name(name, SymbolUsage.GLOBAL, location)
        elif isinstance(statement, ast.Nonlocal):
            for name in statement.names:
                self.register_name(name, SymbolUsage.NONLOCAL, location)
        elif isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
            self.scan_expressions(statement.decorator_list, ExpressionContext.LOAD)
            self.register_name(statement.name, SymbolUsage.ASSIGNED, location)
            if statement.returns is not None:
                self.scan_annotation(statement.returns)
            self.enter_function(statement.name, statement.args, location.row())
            self.scan_statements(statement.body)
            self.leave_scope()
        elif isinstance(statement, ast.ClassDef):
            self.enter_scope(statement.name, SymbolTableType.CLASS, location.row())
            prev_class = self.class_name
            self.class_name = statement.name
            self.register_name("__module__", SymbolUsage.ASSIGNED, location)
            self.register_name("__qualname__", SymbolUsage.ASSIGNED, location)
            self.register_name("__doc__", SymbolUsage.ASSIGNED, location)
            self.register_name("__class__", SymbolUsage.ASSIGNED, location)
            self.scan_statements(statement.body)
            self.leave_scope()
            self.class_name = prev_class
            self.scan_expressions(statement.bases, ExpressionContext.LOAD)
            for keyword in statement.keywords:
                self.scan_expression(keyword.value, ExpressionContext.LOAD)
            self.scan_expressions(statement.decorator_list, ExpressionContext.LOAD)
            self.register_name(statement.name, SymbolUsage.ASSIGNED, location)
        elif isinstance(statement, ast.Expr):
            self.scan_expression(statement.value, ExpressionContext.LOAD)
        elif isinstance(statement, ast.If):
            self.scan_expression(statement.test, ExpressionContext.LOAD)
            self.scan_statements(statement.body)
            self.scan_statements(statement.orelse)
        elif isinstance(statement, (ast.For, ast.AsyncFor)):
            self.scan_expression(statement.target, ExpressionContext.STORE)
            self.scan_expression(statement.iter, ExpressionContext.LOAD)
            self.scan_statements(statement.body)
            self.scan_statements(statement.orelse)
        elif isinstance(statement, ast.While):
            self.scan_expression(statement.test, ExpressionContext.LOAD)
            self.scan_statements(statement.body)
            self.scan_statements(statement.orelse)
        elif isinstance(statement, (ast.Break, ast.Continue, ast.Pass)):
            pass
        elif isinstance(statement, (ast.Import, ast.ImportFrom)):
            for name in statement.names:
                if name.asname is not None:
                    self.register_name(name.asname, SymbolUsage.IMPORTED, location)
                else:
                    self.register_name(
                        name.name.split(".", maxsplit=1)[0],
                        SymbolUsage.IMPORTED,
                        location,
                    )
        elif isinstance(statement, ast.Return):
            if statement.value is not None:
                self.scan_expression(statement.value, ExpressionContext.LOAD)
        elif isinstance(statement, ast.Assert):
            self.scan_expression(statement.test, ExpressionContext.LOAD)
            if statement.msg is not None:
                self.scan_expression(statement.msg, ExpressionContext.LOAD)
        elif isinstance(statement, ast.Delete):
            self.scan_expressions(statement.targets, ExpressionContext.DELETE)
        elif isinstance(statement, ast.Assign):
            self.scan_expressions(statement.targets, ExpressionContext.STORE)
            self.scan_expression(statement.value, ExpressionContext.LOAD)
        elif isinstance(statement, ast.AugAssign):
            self.scan_expression(statement.target, ExpressionContext.STORE)
            self.scan_expression(statement.value, ExpressionContext.LOAD)
        elif isinstance(statement, ast.AnnAssign):
            if isinstance(statement.target, ast.Name):
                self.register_name(
                    statement.target.id, SymbolUsage.ANNOTATION_ASSIGNED, location
                )
            else:
                self.scan_expression(statement.target, ExpressionContext.STORE)
            self.scan_annotation(statement.annotation)
            if statement.value is not None:
                self.scan_expression(statement.value, ExpressionContext.LOAD)
        elif isinstance(statement, ast.With):
            for item in statement.items:
                self.scan_expression(item.context_expr, ExpressionContext.LOAD)
                if item.optional_vars is not None:
                    self.scan_expression(item.optional_vars, ExpressionContext.STORE)
            self.scan_statements(statement.body)
        elif isinstance(statement, ast.Try):
            self.scan_statements(statement.body)
            for handler in statement.handlers:
                if handler.type is not None:
                    self.scan_expression(handler.type, ExpressionContext.LOAD)
                if handler.name is not None:
                    self.register_name(handler.name, SymbolUsage.ASSIGNED, location)
                self.scan_statements(handler.body)
            self.scan_statements(statement.orelse)
            self.scan_statements(statement.finalbody)
        elif isinstance(statement, ast.Raise):
            if statement.exc is not None:
                self.scan_expression(statement.exc, ExpressionContext.LOAD)
            if statement.cause is not None:
                self.scan_expression(statement.cause, ExpressionContext.LOAD)
        else:
            assert False, (statement, ast.unparse(statement))

    def scan_expressions(
        self, expressions: list[ast.expr], context: ExpressionContext
    ) -> None:
        for expression in expressions:
            self.scan_expression(expression, context)

    def scan_expression(self, expression: ast.expr, context: ExpressionContext) -> None:
        # assert (ctx := getattr(expression, "ctx", None)) in (context, None), (
        #     ctx,
        #     context,
        # )
        location = Location.from_ast(expression)
        if isinstance(expression, ast.BinOp):
            self.scan_expression(expression.left, context)
            self.scan_expression(expression.right, context)
        elif isinstance(expression, ast.BoolOp):
            self.scan_expressions(expression.values, context)
        elif isinstance(expression, ast.Compare):
            self.scan_expression(expression.left, context)
            self.scan_expressions(expression.comparators, context)
        elif isinstance(expression, ast.Subscript):
            self.scan_expression(expression.value, ExpressionContext.LOAD)
            self.scan_expression(expression.slice, ExpressionContext.LOAD)
        elif isinstance(expression, ast.Attribute):
            self.scan_expression(expression.value, ExpressionContext.LOAD)
        elif isinstance(expression, ast.Dict):
            for key, value in zip(expression.keys, expression.values):
                if key is not None:
                    self.scan_expression(key, context)
                self.scan_expression(value, context)
        elif isinstance(expression, ast.Await):
            self.scan_expression(expression.value, context)
        elif isinstance(expression, ast.Yield):
            if expression.value is not None:
                self.scan_expression(expression.value, context)
        elif isinstance(expression, ast.YieldFrom):
            self.scan_expression(expression.value, context)
        elif isinstance(expression, ast.UnaryOp):
            self.scan_expression(expression.operand, context)
        elif isinstance(expression, ast.Constant):
            pass
        elif isinstance(expression, ast.Starred):
            self.scan_expression(expression.value, context)
        elif isinstance(expression, (ast.Tuple, ast.Set, ast.List)):
            self.scan_expressions(expression.elts, context)
        elif isinstance(expression, ast.Slice):
            if expression.lower is not None:
                self.scan_expression(expression.lower, context)
            if expression.upper is not None:
                self.scan_expression(expression.upper, context)
            if expression.step is not None:
                self.scan_expression(expression.step, context)
        # elif isinstance(expression, ast.Index):
        #     expression
        #     self.scan_expression(expression.value, context)
        elif isinstance(expression, (ast.GeneratorExp, ast.ListComp, ast.SetComp)):
            self.scan_comprehension(
                "genexpr", expression.elt, None, expression.generators, location
            )
        elif isinstance(expression, ast.DictComp):
            self.scan_comprehension(
                "genexpr",
                expression.key,
                expression.value,
                expression.generators,
                location,
            )
        elif isinstance(expression, ast.Call):
            if context == ExpressionContext.ITER_DEFINITION_EXP:
                self.scan_expression(
                    expression.func, ExpressionContext.ITER_DEFINITION_EXP
                )
            else:
                self.scan_expression(expression.func, ExpressionContext.LOAD)
            self.scan_expressions(expression.args, ExpressionContext.LOAD)
            for keyword in expression.keywords:
                self.scan_expression(keyword.value, ExpressionContext.LOAD)
        elif isinstance(expression, ast.FormattedValue):
            self.scan_expression(expression.value, ExpressionContext.LOAD)
            if expression.format_spec is not None:
                self.scan_expression(expression.format_spec, ExpressionContext.LOAD)
        elif isinstance(expression, ast.JoinedStr):
            for value in expression.values:
                self.scan_expression(value, ExpressionContext.LOAD)
        elif isinstance(expression, ast.Name):
            if context == ExpressionContext.DELETE:
                self.register_name(expression.id, SymbolUsage.ASSIGNED, location)
                self.register_name(expression.id, SymbolUsage.USED, location)
            elif context in (
                ExpressionContext.LOAD,
                ExpressionContext.ITER_DEFINITION_EXP,
            ):
                self.register_name(expression.id, SymbolUsage.USED, location)
            elif context == ExpressionContext.STORE:
                self.register_name(expression.id, SymbolUsage.ASSIGNED, location)
            elif context == ExpressionContext.ITER:
                self.register_name(expression.id, SymbolUsage.ITER, location)

            if (
                context == ExpressionContext.LOAD
                and self.tables[-1].type == SymbolTableType.FUNCTION
                and expression.id == "super"
            ):
                self.register_name("__class__", SymbolUsage.USED, location)
        elif isinstance(expression, ast.Lambda):
            self.enter_function("lambda", expression.args, location.row())
            if context == ExpressionContext.ITER_DEFINITION_EXP:
                self.scan_expression(
                    expression.body, ExpressionContext.ITER_DEFINITION_EXP
                )
            else:
                self.scan_expression(expression.body, ExpressionContext.LOAD)
            self.leave_scope()
        elif isinstance(expression, ast.IfExp):
            self.scan_expression(expression.test, ExpressionContext.LOAD)
            self.scan_expression(expression.body, ExpressionContext.LOAD)
            self.scan_expression(expression.orelse, ExpressionContext.LOAD)
        elif isinstance(expression, ast.NamedExpr):
            if context == ExpressionContext.ITER_DEFINITION_EXP:
                raise SymbolTableError(
                    "assignment expression cannot be used in a comprehension iterable expression",
                    None,
                )

            self.scan_expression(expression.value, ExpressionContext.LOAD)

            if isinstance(expression.target, ast.Name):
                table = self.tables[-1]
                if table.type == SymbolTableType.COMPREHENSION:
                    self.register_name(
                        expression.target.id,
                        SymbolUsage.ASSIGNED_NAMED_EXPR_IN_COMPR,
                        location,
                    )
                else:
                    self.register_name(
                        expression.target.id, SymbolUsage.ASSIGNED, location
                    )
            else:
                self.scan_expression(expression.target, ExpressionContext.STORE)
        else:
            assert False, expression

    def scan_comprehension(
        self,
        scope_name: str,
        elt1: ast.expr,
        elt2: Optional[ast.expr],
        generators: list[ast.comprehension],
        location: Location,
    ) -> None:
        self.enter_scope(scope_name, SymbolTableType.COMPREHENSION, location.row())
        self.register_name(".0", SymbolUsage.PARAMETER, location)
        self.scan_expression(elt1, ExpressionContext.LOAD)
        if elt2 is not None:
            self.scan_expression(elt2, ExpressionContext.LOAD)
        is_first_generator = True
        for generator in generators:
            self.scan_expression(generator.target, ExpressionContext.ITER)
            if is_first_generator:
                is_first_generator = False
            else:
                self.scan_expression(
                    generator.iter, ExpressionContext.ITER_DEFINITION_EXP
                )
            for if_expr in generator.ifs:
                self.scan_expression(if_expr, ExpressionContext.LOAD)
        self.leave_scope()
        assert generators
        self.scan_expression(generators[0].iter, ExpressionContext.ITER_DEFINITION_EXP)

    def enter_function(self, name: str, args: ast.arguments, line_number: int) -> None:
        self.scan_expressions(args.defaults, ExpressionContext.LOAD)
        for expression in args.kw_defaults:
            # FIXME???
            if expression is not None:
                self.scan_expression(expression, ExpressionContext.LOAD)
        self.scan_parameters_annotations(args.posonlyargs)
        self.scan_parameters_annotations(args.args)
        self.scan_parameters_annotations(args.kwonlyargs)
        if args.vararg is not None:
            self.scan_parameter_annotation(args.vararg)
        if args.kwarg is not None:
            self.scan_parameter_annotation(args.kwarg)

        self.enter_scope(name, SymbolTableType.FUNCTION, line_number)

        self.scan_parameters(args.posonlyargs)
        self.scan_parameters(args.args)
        self.scan_parameters(args.kwonlyargs)
        if args.vararg is not None:
            self.scan_parameter(args.vararg)
        if args.kwarg is not None:
            self.scan_parameter(args.kwarg)

    def register_name(self, name: str, role: SymbolUsage, location: Location) -> None:
        scope_depth = len(self.tables)
        table = self.tables[-1]
        name = mangle_name(self.class_name, name)
        # TODO: handle errors
        symbol = table.lookup(name)
        if symbol is None:
            if role == SymbolUsage.NONLOCAL and scope_depth < 2:
                raise SymbolTableError(
                    f"cannot define nonlocal '{name}' at top level.", location
                )
            symbol = table.symbols[name] = Symbol(name)

        if role == SymbolUsage.NONLOCAL:
            symbol.scope = SymbolScope.FREE
            symbol.is_nonlocal = True
        elif role == SymbolUsage.IMPORTED:
            symbol.is_assigned = True
            symbol.is_imported = True
        elif role == SymbolUsage.PARAMETER:
            symbol.is_parameter = True
        elif role == SymbolUsage.ANNOTATION_PARAMETER:
            symbol.is_parameter = True
            symbol.is_annotated = True
        elif role == SymbolUsage.ANNOTATION_ASSIGNED:
            symbol.is_assigned = True
            symbol.is_annotated = True
        elif role == SymbolUsage.ASSIGNED:
            symbol.is_assigned = True
        elif role == SymbolUsage.ASSIGNED_NAMED_EXPR_IN_COMPR:
            symbol.is_assigned = True
            symbol.is_assign_namedexpr_in_comprehension = True
        elif role == SymbolUsage.GLOBAL:
            symbol.scope = SymbolScope.GLOBAL_EXPLICIT
        elif role == SymbolUsage.USED:
            symbol.is_referenced = True
        elif role == SymbolUsage.ITER:
            symbol.is_iter = True
        else:
            assert False, role

        if symbol.is_iter and symbol.is_assigned:
            raise SymbolTableError(
                "assignment expression cannot be used in a comprehension iterable expression",
                None,
            )


def mangle_name(class_name: Optional[str], name: str) -> str:
    if class_name is None:
        return name
    if not name.startswith("__") or name.endswith("__") or "." in name:
        return name
    if class_name.startswith("_"):
        return class_name + name
    return "_" + class_name + name


def make_symbol_table(program: list[ast.stmt]) -> SymbolTable:
    builder = SymbolTableBuilder.new()
    builder.scan_statements(program)
    return builder.finish()


def make_symbol_table_expr(expr: ast.expr) -> SymbolTable:
    builder = SymbolTableBuilder.new()
    builder.scan_expression(expr, ExpressionContext.LOAD)
    return builder.finish()
