# import compiler.symboltable as symboltable
# import ast

# a = ast.parse(open("compiler/symboltable.py").read())

# stb = symboltable.SymbolTableBuilder.new()
# stb.scan_statements(a.body)
# st = stb.finish()
# print(st)

from compiler.compile import CompileError
from compiler.mode import Mode
from vm.vm import Interpreter, VirtualMachine

def do(vm: VirtualMachine) -> None:
    scope = vm.new_scope_with_builtins()
    try:
        code_obj = vm.compile("x = 'running'", Mode.Exec, "<embedded>")
    except CompileError as e:
        vm.new_syntax_error(e)
    vm.run_code_object(code_obj, scope)


Interpreter.default().enter(do)
