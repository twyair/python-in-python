from __future__ import annotations
from typing import TYPE_CHECKING

from compiler.compile import CompileError
from compiler.mode import Mode
import compiler.porcelain
from vm.exceptions import PyBaseExceptionRef
from vm.function_ import FuncArgs
from vm.scope import Scope
import vm.builtins.code as pycode
import vm.vm as vm_

# from vm.vm import enter_vm

if TYPE_CHECKING:
    from vm.pyobjectrc import PyObjectRef
    from vm.builtins.pystr import PyStrRef
    from vm.vm import VirtualMachine, InitParameter


def init_importlib(vm: VirtualMachine, initialize_parameter: InitParameter) -> None:
    from vm.vm import InitParameter

    # #[cfg(all(feature = "threading", not(target_os = "wasi")))]
    # import_builtin(vm, "_thread")?;
    # import_builtin(vm, "_warnings")
    # import_builtin(vm, "_weakref")

    def do() -> PyObjectRef:
        importlib = import_frozen(vm, "_frozen_importlib")
        impmod = import_builtin(vm, "_imp")
        install = importlib.get_attr(vm.ctx.new_str("_install"), vm)
        vm.invoke(install, FuncArgs([vm.sys_module, impmod]))
        return importlib

    importlib = vm_.enter_vm(vm, do)
    vm.import_func = importlib.get_attr(vm.ctx.new_str("__import__"), vm)

    if initialize_parameter == InitParameter.External:
        pass
        # TODO
        # raise NotImplementedError


def import_frozen(vm: VirtualMachine, module_name: str) -> PyObjectRef:
    v = vm.state.frozen.get(module_name)
    if v is None:
        vm.new_import_error(
            f"Cannot import frozen module {module_name}", vm.ctx.new_str(module_name)
        )
    return import_codeobj(vm, module_name, v.code, False)


def import_builtin(vm: VirtualMachine, module_name: str) -> PyObjectRef:
    make_module_func = vm.state.module_inits.get(module_name)
    if make_module_func is None:
        vm.new_import_error(
            f"Cannot import builtin module {module_name}", vm.ctx.new_str(module_name)
        )
    module = make_module_func(vm)
    sys_modules = vm.sys_module.get_attr(vm.ctx.new_str("modules"), vm)
    sys_modules.set_item(vm.ctx.new_str(module_name), module, vm)
    return module


def import_file(
    vm: VirtualMachine, module_name: str, file_path: str, content: str
) -> PyObjectRef:
    try:
        code_obj = compiler.porcelain.compile(
            content, Mode.Exec, file_path, vm.compile_opts()
        )
    except CompileError as err:
        vm.new_syntax_error(err)
    return import_codeobj(vm, module_name, vm.map_codeobj(code_obj), True)


def import_codeobj(
    vm: VirtualMachine,
    module_name: str,
    code_obj: pycode.CodeObject[pycode.PyConstant, PyStrRef],
    set_file_attr: bool,
) -> PyObjectRef:
    attrs = vm.ctx.new_dict()
    attrs._.set_item(vm.ctx.new_str("__name__"), vm.ctx.new_str(module_name), vm)
    if set_file_attr:
        attrs._.set_item(vm.ctx.new_str("__file__"), code_obj.source_path, vm)
    module = vm.new_module(module_name, attrs, None)

    vm.sys_module.get_attr(vm.ctx.new_str("modules"), vm).set_item(
        vm.ctx.new_str(module_name), module, vm
    )

    vm.run_code_object(
        pycode.PyCode(code_obj).into_ref(vm), Scope.with_builtins(None, attrs, vm)
    )
    return module


def remove_importlib_frames(
    vm: VirtualMachine, exc: PyBaseExceptionRef
) -> PyBaseExceptionRef:
    return exc  # TODO!!!
