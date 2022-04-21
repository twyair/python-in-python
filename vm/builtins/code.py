from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar, TypeAlias

if TYPE_CHECKING:

    from vm.builtins.tuple import PyTupleRef
    from vm.pyobject import PyContext
    from vm.pyobjectrc import PyRef
    from bytecode.bytecode import ConstantData, CodeObject
    from vm.builtins.pytype import PyTypeRef
    from vm.vm import VirtualMachine

import bytecode.bytecode as bytecode
import vm.builtins.pystr as pystr
import vm.function_ as fn
import vm.pyobject as po
import vm.pyobjectrc as prc

from common.deco import pymethod, pyproperty, pyslot


@dataclass
class PyConstant:
    value: prc.PyObjectRef

    # TODO: types
    def map_constant(self, bag: Any) -> Any:
        return bag.make_constant(self.value)


FrozenModule: TypeAlias = bytecode.FrozenModule["PyConstant", pystr.PyStrRef]


@dataclass
class PyObjBag:
    value: VirtualMachine

    def make_constant(self, constant: ConstantData) -> PyConstant:
        return PyConstant(constant.to_pyobj(self.value))

    def make_name(self, name: str) -> pystr.PyStrRef:
        # TODO: `return self.value.intern_string(name)`
        return self.value.ctx.new_str(name)


# TODO: impl ConstantBag for PyObjBag


@po.pyimpl(py_ref=True)
@po.pyclass("code")
@dataclass
class PyCode(po.PyClassImpl):
    code: CodeObject[PyConstant, pystr.PyStrRef]

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.code_type

    @pyslot
    @staticmethod
    def slot_new(
        class_: PyTypeRef, args: fn.FuncArgs, vm: VirtualMachine
    ) -> prc.PyObjectRef:
        vm.new_type_error("Cannot directly create code object")

    @pymethod(True)
    @staticmethod
    def i__repr__(zelf: PyRef[PyCode], vm: VirtualMachine) -> str:
        code = zelf._.code
        return f"<code object {code.obj_name} at {zelf.get_id()} file {code.source_path._.as_str()}, line {code.first_line_number}>"

    @pyproperty()
    @staticmethod
    def get_co_posonlyargcount(zelf: PyRef[PyCode], *, vm: VirtualMachine) -> int:
        return zelf._.code.posonlyarg_count

    @pyproperty()
    @staticmethod
    def get_co_argcount(zelf: PyRef[PyCode], *, vm: VirtualMachine) -> int:
        return zelf._.code.arg_count

    @pyproperty()
    @staticmethod
    def get_co_filename(zelf: PyRef[PyCode], *, vm: VirtualMachine) -> pystr.PyStrRef:
        return zelf._.code.source_path

    @pyproperty()
    @staticmethod
    def get_co_firstlineno(zelf: PyRef[PyCode], *, vm: VirtualMachine) -> int:
        return zelf._.code.first_line_number

    @pyproperty()
    @staticmethod
    def get_co_kwonlyargcount(zelf: PyRef[PyCode], *, vm: VirtualMachine) -> int:
        return zelf._.code.kwonlyarg_count

    @pyproperty()
    @staticmethod
    def get_co_consts(zelf: PyRef[PyCode], *, vm: VirtualMachine) -> PyTupleRef:
        return vm.ctx.new_tuple([x.value for x in zelf._.code.constants])

    @pyproperty()
    @staticmethod
    def get_co_name(zelf: PyRef[PyCode], *, vm: VirtualMachine) -> pystr.PyStrRef:
        return zelf._.code.obj_name

    @pyproperty()
    @staticmethod
    def get_co_flags(zelf: PyRef[PyCode], *, vm: VirtualMachine) -> int:
        return zelf._.code.flags.value

    @pyproperty()
    @staticmethod
    def get_co_varnames(zelf: PyRef[PyCode], *, vm: VirtualMachine) -> PyTupleRef:
        return vm.ctx.new_tuple([x for x in zelf._.code.varnames])


def init(ctx: PyContext) -> None:
    PyCode.extend_class(ctx, ctx.types.code_type)
