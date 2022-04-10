from __future__ import annotations
from bytecode.bytecode import CodeObject
from compiler.compile import CompileError, CompileOpts, compile_top
from compiler.mode import Mode
import ast

def compile(source: str, mode: Mode, source_path: str, opts: CompileOpts) -> CodeObject:
    try:
        ast_ = ast.parse(source, mode=mode.value)
    except SyntaxError as e:
        raise CompileError.from_parse(e, source, source_path)
    if opts.optimize > 0:
        raise NotImplementedError
    return compile_top(ast_, source_path, opts)