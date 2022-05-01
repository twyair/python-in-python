from common.error import PyImplBase, PyImplError, PyImplException
from compiler.compile import CompileError
from compiler.mode import Mode
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
        if (tr := exc.exception._.traceback) is not None:
            print("TRACEBACK: line =", tr._.lineno)
        name = str(exc.exception.class_()._.name())[2:]
        print(f"{name}: ...")
    elif isinstance(exc, PyImplError):
        print(f"PyImplError: obj-type = {exc.obj.class_()._.name()}")


def do(vm: VirtualMachine) -> None:
    scope = vm.new_scope_with_builtins()
    with open("test_int.py") as f:
        prog = f.read()
    try:
        code_obj = vm.compile(
            prog,
            Mode.Exec,
            "<embedded>",
        )
    except CompileError as e:
        vm.new_syntax_error(e)

    try:
        vm.run_code_object(code_obj, scope)
    except PyImplBase as e:
        print_exception(e)
        raise
    # try:
    #     repr_ = res.repr(vm)._.as_str()
    # except PyImplBase as e:
    #     print_exception(e)
    #     raise

    # print(
    #     res.class_()._.name(),
    #     repr_,
    # )


settings = PySettings(dont_write_bytecode=True, no_user_site=True)
settings.path_list.append("/home/yair/workspace/RustPython/Lib/")
interpreter = Interpreter.new_with_init(settings, lambda vm: InitParameter.External)
# Interpreter.default().enter(do)
interpreter.enter(do)
