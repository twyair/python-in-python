# import compiler.symboltable as symboltable
# import ast

# a = ast.parse(open("compiler/symboltable.py").read())

# stb = symboltable.SymbolTableBuilder.new()
# stb.scan_statements(a.body)
# st = stb.finish()
# print(st)

from common.error import PyImplBase, PyImplError, PyImplException
from compiler.compile import CompileError
from compiler.mode import Mode
from vm.pyobjectrc import PyObjectRef
from vm.vm import Interpreter, VirtualMachine


def repl(vm: VirtualMachine) -> None:
    scope = vm.new_scope_with_builtins()
    while True:
        line = input(">>> ")
        try:
            code_obj = vm.compile(line, Mode.Eval, "<repl>")
            # code_obj = vm.compile(line, Mode.Single, "<repl>")
        except CompileError as e:
            vm.new_syntax_error(e)
        try:
            res = vm.run_code_object(code_obj, scope)
        except PyImplBase as e:
            print(f"exception: {type(e)}")
        except BaseException:
            raise
        else:
            if not vm.is_none(res):
                scope.globals._.set_item(vm.mk_str("last"), res, vm)
                print(f"last: {res.class_()._.name()} = {res.repr(vm)._.as_str()}")


def print_exception(exc: PyImplBase) -> None:
    if isinstance(exc, PyImplException):
        name = str(exc.exception.class_()._.name())[2:]
        print(f"{name}: ...")
    elif isinstance(exc, PyImplError):
        print(f"PyImplError: obj-type = {exc.obj.class_()._.name()}")


def do(vm: VirtualMachine) -> None:
    scope = vm.new_scope_with_builtins()
    try:
        # code_obj = vm.compile("x = 'running' * 3", Mode.Exec, "<embedded>")
        code_obj = vm.compile(
            # "callable(abs)",
            "repr(3j * 3 + 5j - 3.0)",
            # "[3j] * 3",
            # "bool(5.0)",
            # "'sss' + 'abcd'",
            Mode.Eval,
            "<embedded>",
        )
    except CompileError as e:
        vm.new_syntax_error(e)

    try:
        res = vm.run_code_object(code_obj, scope)
    except PyImplBase as e:
        print_exception(e)
        return
    try:
        repr_ = res.repr(vm)._.as_str()
    except PyImplBase as e:
        print_exception(e)
        raise

    print(
        res.class_()._.name(),
        repr_,
    )


Interpreter.default().enter(do)
