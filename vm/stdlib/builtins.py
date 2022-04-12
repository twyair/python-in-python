from __future__ import annotations
from typing import TYPE_CHECKING, Optional


if TYPE_CHECKING:
    from vm.vm import VirtualMachine
    from vm.function_ import FuncArgs
    from vm.pyobjectrc import PyObjectRef

import vm.function_ as fn
import vm.pyobjectrc as prc
import vm.pyobject as po
import vm.builtins.pystr as pystr
import vm.stdlib.sys as std_sys
from common.deco import pyfunction, pymodule
import vm.function.arguments as arg


@pymodule
class builtins(po.PyModuleImpl):
    @pyfunction
    @staticmethod
    def abs(x: PyObjectRef, /, *, vm: VirtualMachine) -> PyObjectRef:
        return vm._abs(x)

    # @pyfunction
    # @staticmethod
    # def all(iterable: arg.ArgIterable, vm: VirtualMachine) -> PyObjectRef:
    #     for item in iterable.iter(vm):
    #         if not item.to_bool():
    #             return vm.ctx.new_bool(False)
    #     return vm.ctx.new_bool(True)

    # @pyfunction
    # @staticmethod
    # def any(iterable: arg.ArgIterable, vm: VirtualMachine) -> PyObjectRef:
    #     for item in iterable.iter(vm):
    #         if item.to_bool():
    #             return vm.ctx.new_bool(True)
    #     return vm.ctx.new_bool(False)

    # @pyfunction
    # @staticmethod
    # def ascii(obj: PyObjectRef, /, *, vm: VirtualMachine) -> PyObjectRef:
    #     raise NotImplementedError

    # @pyfunction
    # @staticmethod
    # def bin(obj: PyObjectRef, /, *, vm: VirtualMachine) -> PyObjectRef:
    #     raise NotImplementedError

    @pyfunction
    @staticmethod
    def callable(obj: PyObjectRef, /, *, vm: VirtualMachine) -> PyObjectRef:
        return vm.ctx.new_bool(vm.is_callable(obj))

    # # TODO: impl chr(), compile(), ...

    @pyfunction
    @staticmethod
    def delattr(
        obj: PyObjectRef, attr: pystr.PyStrRef, /, *, vm: VirtualMachine
    ) -> None:
        obj.del_attr(attr, vm)

    # # TODO: impl dir

    @pyfunction
    @staticmethod
    def divmod(a: PyObjectRef, b: PyObjectRef, /, *, vm: VirtualMachine) -> PyObjectRef:
        return vm._divmod(a, b)

    # # TODO: impl eval(), exec(), format(),

    @pyfunction
    @staticmethod
    def getattr(
        obj: PyObjectRef,
        attr: pystr.PyStrRef,
        default: Optional[PyObjectRef] = None,
        /,
        *,
        vm: VirtualMachine,
    ) -> PyObjectRef:
        if default is not None:
            r = vm.get_attribute_opt(obj, attr)
            if r is None:
                return default
            return r
        else:
            return obj.get_attr(attr, vm)

    # @pyfunction
    # @staticmethod
    # def print(
    #     *args: PyObjectRef,
    #     sep: Optional[PyObjectRef] = None,
    #     end: Optional[PyObjectRef] = None,
    #     flush: Optional[PyObjectRef] = None,
    #     file: Optional[PyObjectRef] = None,
    #     vm: VirtualMachine,
    # ) -> None:
    #     if file is None or vm.is_none(file):
    #         file = std_sys.sys.get_stdout(vm)

    #     write = lambda obj: vm.call_method(file, "write", fn.FuncArgs([obj]))

    #     if sep is None or vm.is_none(sep):
    #         sep = pystr.PyStr.from_str(" ", vm.ctx)

    #     first = True
    #     for object in args:
    #         if first:
    #             first = False
    #         else:
    #             write(sep)

    #         write(object.str(vm))

    #     if end is None or vm.is_none(end):
    #         end = pystr.PyStr.from_str("\n", vm.ctx)

    #     write(end)

    #     if flush is not None and flush.try_to_bool(vm):
    #         vm.call_method(file, "flush", fn.FuncArgs())

    #     return None

    @pyfunction
    @staticmethod
    def repr(obj: PyObjectRef, /, *, vm: VirtualMachine) -> PyObjectRef:
        return obj.repr(vm)


def make_module(vm: VirtualMachine, module: PyObjectRef) -> None:
    builtins.extend_module(vm, module)

    # TODO
