from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Iterable, Optional
from compiler.mode import Mode
import vm.builtins.code as code
import bytecode.bytecode as bytecode
import bytecode.frozen_lib
import compiler.compile
import compiler.porcelain

if TYPE_CHECKING:
    from vm.vm import VirtualMachine


def map_frozen(
    vm: VirtualMachine, i: Iterable[tuple[str, bytecode.FrozenModule]]
) -> Iterable[tuple[str, code.FrozenModule]]:
    return [
        (k, code.FrozenModule(vm.map_codeobj(mod.code), mod.package)) for k, mod in i
    ]


@dataclass
class CompilationSource(ABC):
    def compile_string(
        self, source: str, mode: Mode, module_name: str, origin: Callable[[], str]
    ) -> bytecode.CodeObject:
        return compiler.porcelain.compile(
            source, mode, module_name, compiler.compile.CompileOpts(0)
        )

    @abstractmethod
    def compile(self, mode: Mode, module_name: str) -> dict[str, code.FrozenModule]:
        ...


@dataclass
class CompilationSourceFile(CompilationSource):
    value: Path

    def compile(self, mode: Mode, module_name: str) -> dict[str, code.FrozenModule]:
        raise NotImplementedError


@dataclass
class CompilationSourceCode(CompilationSource):
    value: str

    def compile(self, mode: Mode, module_name: str) -> dict[str, code.FrozenModule]:
        return {
            module_name: code.FrozenModule(
                self.compile_string(self.value, mode, module_name, lambda: "TODO"),
                False,
            )
        }


@dataclass
class CompilationSourceDir(CompilationSource):
    value: Path

    def compile(self, mode: Mode, module_name: str) -> dict[str, code.FrozenModule]:
        return self.compile_dir(self.value, "", mode)

    # TODO: handle errors
    def compile_dir(
        self, path_: Path, parent: str, mode: Mode
    ) -> dict[str, code.FrozenModule]:
        code_map = {}
        for path in path_.iterdir():
            file_name = path.name
            if path.is_dir():
                code_map.update(self.compile_dir(path, f"{parent}{file_name}", mode))
            elif file_name.endswith(".py"):
                stem = path.stem
                is_init = stem == "__init__"
                if is_init:
                    module_name = parent
                elif not parent:
                    module_name = stem
                else:
                    module_name = f"{parent}.{stem}"

                def compile_path(src_path: Path):
                    source = src_path.read_text()
                    return self.compile_string(
                        source, mode, module_name, lambda: "TODO"
                    )

                code_map[module_name] = code.FrozenModule(compile_path(path), is_init)
        return code_map


@dataclass
class CompileArgs:
    source: CompilationSource
    mode: Mode
    module_name: str
    # crate_name: str  # TODO?


def py_freeze(
    *,
    mode: Mode = Mode.Exec,
    module_name: str = "frozen",
    source: Optional[str] = None,
    file: Optional[str] = None,
    dir: Optional[str] = None,
    # crate_name: Optional[str] = None,  # TODO?
) -> Iterable[tuple[str, code.FrozenModule]]:
    source_ = None
    if source is not None:
        assert source_ is None
        source_ = CompilationSourceCode(source)
    if file is not None:
        assert source_ is None
        source_ = CompilationSourceFile(Path(file))
    if dir is not None:
        assert source_ is None
        source_ = CompilationSourceDir(Path(dir))
    assert source_ is not None
    args = CompileArgs(source=source_, mode=mode, module_name=module_name)

    code_map = args.source.compile(args.mode, args.module_name)
    data = bytecode.frozen_lib.encode_lib(code_map.items())
    return bytecode.frozen_lib.decode_lib(data)


def get_module_inits() -> Iterable[tuple[str, code.FrozenModule]]:
    ls: list[tuple[str, code.FrozenModule]] = []

    def ext_modules(**kwargs):
        ls.extend(py_freeze(**kwargs))

    # ext_modules(source="initialized = True", module_name="__hello__")  # TODO?
    ext_modules(dir="/home/yair/workspace/RustPython/vm/Lib/python_builtins/")
    ext_modules(dir="/home/yair/workspace/RustPython/vm/Lib/core_modules/")

    return ls
