from pathlib import Path
from common.error import PyImplBase, PyImplError, PyImplException
from compiler.compile import CompileError
from compiler.mode import Mode
from vm.builtins.int import PyInt
from vm.vm import InitParameter, Interpreter, PySettings, VirtualMachine


def repl(vm: VirtualMachine) -> None:
    scope = vm.new_scope_with_builtins()
    while True:
        line = input(">>> ")
        try:
            # code_obj = vm.compile(line, Mode.Eval, "<repl>")
            code_obj = vm.compile(line, Mode.Single, "<repl>")
        except CompileError as e:
            vm.new_syntax_error(e)
        try:
            res = vm.run_code_object(code_obj, scope)
        except PyImplBase as e:
            print_exception(e)
        except BaseException:
            raise
        else:
            if not vm.is_none(res):
                scope.globals._.set_item(vm.mk_str("last"), res, vm)
                print(f"last: {res.class_()._.name()} = {res.repr(vm)._.as_str()}")


def print_exception(exc: PyImplBase) -> None:
    if isinstance(exc, PyImplException):
        tr = exc.exception._.traceback
        if tr is not None:
            print("TRACEBACK: line =", tr._.lineno)
            tr = tr._.next
        name = str(exc.exception.class_()._.name())
        print(f"{name}: ...")
    elif isinstance(exc, PyImplError):
        print(f"PyImplError: obj-type = {exc.obj.class_()._.name()}")


def do(vm: VirtualMachine) -> None:
    scope = vm.new_scope_with_builtins()
    with open("prog.py") as f:
        prog = f.read()
    try:
        code_obj = vm.compile(
            prog,
            Mode.Exec,
            "prog.py",
        )
    except CompileError as e:
        vm.new_syntax_error(e)

    try:
        vm.run_code_object(code_obj, scope)
    except PyImplException as e:
        vm.print_exception(e.exception)
    except PyImplError as e:
        print(f"PyImplError: obj-type = {e.obj.class_()._.name()}")
        raise


settings = PySettings(dont_write_bytecode=True, no_user_site=True)
settings.path_list.append(str((Path.cwd() / "cpython" / "Lib").resolve()))
interpreter = Interpreter.new_with_init(settings, lambda vm: InitParameter.External)
# Interpreter.default().enter(do)
try:
    interpreter.enter(do)
except PyImplException as e:
    print(e.exception.type._.name())
    print(e.exception._.args._.fast_getitem(0).debug_repr())
