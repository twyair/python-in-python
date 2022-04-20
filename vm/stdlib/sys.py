from __future__ import annotations
from typing import TYPE_CHECKING, Optional
from vm.function_ import FuncArgs


if TYPE_CHECKING:
    from vm.pyobjectrc import PyObjectRef, PyObject, PyRef
    from vm.vm import VirtualMachine

import vm.pyobject as po
import vm.builtins.list as pylist
import vm.builtins.tuple as pytuple
import vm.builtins.dict as pydict
import vm.builtins.namespace as pynamespace
from vm import extend_module
from common.deco import pyfunction, pymodule, pyattr
from common.error import PyImplBase
from common import CHAR_MAX, ISIZE_MAX


def option_env(s: str) -> Optional[str]:
    return None
    # raise NotImplementedError


@pymodule
class sys(po.PyModuleImpl):
    attr_multiarch: None = None  # TODO
    attr_abiflags: str = ""
    attr_api_version: int = 0x0
    attr_copyright: str = ""
    attr_float_repr_style: str = "short"
    attr__framework: str = ""
    attr_hexversion: int = 0  # TODO: `version.VERSION_HEX`
    attr_maxsize: int = ISIZE_MAX
    attr_maxunicode: int = CHAR_MAX
    attr_platform: str = "unknown"  # TODO
    attr_ps1: str = ">>>>> "
    attr_ps2: str = "..... "

    @pyattr
    @staticmethod
    def default_prefix(vm: VirtualMachine) -> str:
        return "/usr/local"

    @pyattr
    @staticmethod
    def prefix(vm: VirtualMachine) -> str:
        return option_env("RUSTPYTHON_PREFIX") or sys.default_prefix(vm)

    @pyattr
    @staticmethod
    def base_prefix(vm: VirtualMachine) -> str:
        return option_env("RUSTPYTHON_BASEPREFIX") or sys.prefix(vm)

    @pyattr
    @staticmethod
    def exec_prefix(vm: VirtualMachine) -> str:
        return option_env("RUSTPYTHON_BASEPREFIX") or sys.prefix(vm)

    @pyattr
    @staticmethod
    def base_exec_prefix(vm: VirtualMachine) -> str:
        return option_env("RUSTPYTHON_BASEPREFIX") or sys.exec_prefix(vm)

    @pyattr
    @staticmethod
    def platlibdir(vm: VirtualMachine) -> str:
        return option_env("RUSTPYTHON_PLATLIBDIR") or "lib"

    @pyattr
    @staticmethod
    def argv(vm: VirtualMachine) -> pylist.PyListRef:
        return vm.ctx.new_list([vm.ctx.new_str(x) for x in vm.state.settings.argv])

    # @pyattr
    # @staticmethod
    # def builtin_module_names(vm: VirtualMachine) -> pytuple.PyTupleRef:
    #     raise NotImplementedError

    # @pyattr
    # @staticmethod
    # def byteorder(vm: VirtualMachine) -> str:
    #     raise NotImplementedError

    # @pyattr
    # @staticmethod
    # def _base_executable(vm: VirtualMachine) -> PyObjectRef:
    #     raise NotImplementedError

    @pyattr
    @staticmethod
    def dont_write_bytecode(vm: VirtualMachine) -> bool:
        return vm.state.settings.dont_write_bytecode

    # @pyattr
    # @staticmethod
    # def executable(vm: VirtualMachine) -> PyObjectRef:
    #     raise NotImplementedError

    # @pyattr
    # @staticmethod
    # def _git(vm: VirtualMachine) -> pytuple.PyTupleRef:
    #     raise NotImplementedError
    #     # return vm.ctx.new_tuple([vm.ctx.new_str("Python"), ])

    # @pyattr
    # @staticmethod
    # def implementation(vm: VirtualMachine) -> PyRef[pynamespace.PyNamespace]:
    #     raise NotImplementedError

    @pyattr
    @staticmethod
    def meta_path(vm: VirtualMachine) -> pylist.PyListRef:
        return vm.ctx.new_list([])

    @pyattr
    @staticmethod
    def path(vm: VirtualMachine) -> pylist.PyListRef:
        return vm.ctx.new_list([vm.ctx.new_str(x) for x in vm.state.settings.path_list])

    @pyattr
    @staticmethod
    def path_hooks(vm: VirtualMachine) -> pylist.PyListRef:
        return vm.ctx.new_list([])

    @pyattr
    @staticmethod
    def path_importer_cache(vm: VirtualMachine) -> pydict.PyDictRef:
        return vm.ctx.new_dict()

    @pyattr
    @staticmethod
    def pycache_prefix(vm: VirtualMachine) -> PyObjectRef:
        return vm.ctx.get_none()

    # @pyattr
    # @staticmethod
    # def version(vm: VirtualMachine) -> str:
    #     raise NotImplementedError
    #     # return version.get_version()

    # @pyattr
    # @staticmethod
    # def _xoptions(vm: VirtualMachine) -> pydict.PyDictRef:
    #     raise NotImplementedError

    @pyattr
    @staticmethod
    def warnoptions(vm: VirtualMachine) -> pylist.PyListRef:
        return vm.ctx.new_list([vm.ctx.new_str(x) for x in vm.state.settings.warnopts])

    @pyfunction(False)
    @staticmethod
    def audit(args: FuncArgs, *, vm: VirtualMachine) -> None:
        raise NotImplementedError

    @pyfunction(False)
    @staticmethod
    def exit(code: Optional[PyObjectRef] = None, *, vm: VirtualMachine) -> PyObjectRef:
        code = vm.unwrap_or_none(code)
        vm.new_exception(vm.ctx.exceptions.system_exit, [code])

    @pyfunction
    @staticmethod
    def displayhook(obj: PyObjectRef, *, vm: VirtualMachine) -> None:
        raise NotImplementedError

    @pyfunction
    @staticmethod
    def i__displayhook__(obj: PyObjectRef, *, vm: VirtualMachine) -> None:
        return sys.displayhook(obj, vm=vm)

    @pyfunction
    @staticmethod
    def excepthook(
        exc_type: PyObjectRef,
        exc_val: PyObjectRef,
        exc_tb: PyObjectRef,
        *,
        vm: VirtualMachine,
    ) -> None:
        exc = vm.normalize_exception(exc_type, exc_val, exc_tb)
        stderr = get_stderr(vm)
        # vm.write_exception()
        raise NotImplementedError

    @pyfunction
    @staticmethod
    def i__excepthook__(
        exc_type: PyObjectRef,
        exc_val: PyObjectRef,
        exc_tb: PyObjectRef,
        *,
        vm: VirtualMachine,
    ) -> None:
        return sys.excepthook(exc_type, exc_val, exc_tb, vm=vm)

    @pyfunction
    @staticmethod
    def exc_info(*, vm: VirtualMachine) -> pytuple.PyTupleRef:
        exc = vm.topmost_exception()
        if exc is not None:
            return vm.ctx.new_tuple(list(vm.split_exception(exc)))
        else:
            return vm.ctx.new_tuple(
                [vm.ctx.get_none(), vm.ctx.get_none(), vm.ctx.get_none()]
            )

    # @pyattr
    # @staticmethod
    # def flags(vm: VirtualMachine) -> pytuple.PyTupleRef:
    #     raise NotImplementedError

    # @pyattr
    # @staticmethod
    # def float_info(vm: VirtualMachine) -> pytuple.PyTupleRef:
    #     raise NotImplementedError

    @pyfunction
    @staticmethod
    def getdefaultencoding(*, vm: VirtualMachine) -> str:
        raise NotImplementedError
        # return codecs.DEFAULT_ENCODING

    @pyfunction
    @staticmethod
    def getrefcount(obj: PyObjectRef, *, vm: VirtualMachine) -> int:
        raise NotImplementedError

    @pyfunction
    @staticmethod
    def getrecursionlimit(*, vm: VirtualMachine) -> int:
        return vm.recursion_limit

    @pyfunction
    @staticmethod
    def getsizeof(obj: PyObjectRef, *, vm: VirtualMachine) -> int:
        raise NotImplementedError

    # impl functions from line 351 ...


def __get_stdio(name: str, vm: VirtualMachine) -> PyObjectRef:

    try:
        return vm.sys_module.get_attr(vm.mk_str(name), vm)
    except PyImplBase as _:
        vm.new_runtime_error(f"lost sys.{name}")


def get_stdout(vm: VirtualMachine) -> PyObjectRef:
    return __get_stdio("stdout", vm)


def get_stdin(vm: VirtualMachine) -> PyObjectRef:
    return __get_stdio("stdin", vm)


def get_stderr(vm: VirtualMachine) -> PyObjectRef:
    return __get_stdio("stderr", vm)


def sysconfigdata_name() -> str:
    return "_sysconfigdata_{}_{}_{}".format(
        sys.attr_abiflags, sys.attr_platform, sys.attr_multiarch
    )


def init_module(vm: VirtualMachine, module: PyObject, builtins: PyObject) -> None:
    # TODO:
    # sys.Flags.make_class(vm.ctx)

    sys.extend_module(vm, module)

    modules = vm.ctx.new_dict()
    modules.set_item(vm.ctx.new_str("sys"), module, vm)
    modules.set_item(vm.ctx.new_str("builtins"), builtins, vm)
    extend_module(
        vm,
        module,
        {
            # "__doc__": None,  # TODO
            "modules": modules,
        },
    )
