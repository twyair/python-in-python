from __future__ import annotations
import random
from typing import TYPE_CHECKING
from common.error import PyImplBase

from compiler.compile import CompileError
from compiler.mode import Mode
import compiler.porcelain
from vm.exceptions import PyBaseExceptionRef
import vm.function_ as fn
from vm.scope import Scope
import vm.builtins.code as pycode
import vm.builtins.list as pylist
import vm.vm as vm_


if TYPE_CHECKING:
    from vm.pyobjectrc import PyObjectRef
    from vm.builtins.pystr import PyStrRef
    from vm.vm import VirtualMachine


def init_importlib(vm: VirtualMachine, initialize_parameter: vm_.InitParameter) -> None:

    import_builtin(vm, "_thread")
    import_builtin(vm, "_warnings")
    import_builtin(vm, "_weakref")

    def do() -> PyObjectRef:
        importlib = import_frozen(vm, "_frozen_importlib")
        impmod = import_builtin(vm, "_imp")
        install = importlib.get_attr(vm.ctx.new_str("_install"), vm)
        # FIXME
        vm.invoke(install, fn.FuncArgs([vm.sys_module, impmod]))
        return importlib

    importlib = vm_.enter_vm(vm, do)
    vm.import_func = importlib.get_attr(vm.ctx.new_str("__import__"), vm)

    if initialize_parameter == vm_.InitParameter.External:

        def init_external() -> None:
            import_builtin(vm, "_io")
            return
            import_builtin(vm, "marshal")

            install_external = importlib.get_attr(
                vm.ctx.new_str("_install_external_importers"), vm
            )
            vm.invoke(install_external, fn.FuncArgs())

            importlib_external = vm.import_(
                vm.ctx.new_str("_frozen_importlib_external"), None, 0
            )
            magic_bytes = b""  # TODO: `get_git_revision()[:4]`
            if len(magic_bytes) != 4:
                magic_bytes = random.randbytes(4)
            magic = vm.ctx.new_bytes(magic_bytes)
            importlib_external.set_attr(vm.ctx.new_str("MAGIC_NUMBER"), magic, vm)
            try:
                zipimport = vm.import_(vm.ctx.new_str("zipimport"), None, 0)
                zipimporter = zipimport.get_attr(vm.ctx.new_str("zipimporter"), vm)
                path_hooks = pylist.PyList.try_from_object(
                    vm, vm.sys_module.get_attr(vm.ctx.new_str("path_hooks"), vm)
                )
                path_hooks._.insert(0, zipimporter, vm=vm)
            except PyImplBase as _:
                pass
                # TODO:
                # warn("couldn't init zipimport")

        vm_.enter_vm(vm, init_external)


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
