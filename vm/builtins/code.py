from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar, Generic

if TYPE_CHECKING:

    # from vm.builtins.pystr import PyStrRef
    from vm.pyobject import PyContext
    from vm.pyobjectrc import PyRef
    from bytecode.bytecode import ConstantData, CT, CodeObject
    from vm.builtins.pytype import PyTypeRef
    from vm.vm import VirtualMachine
from common.deco import pymethod
import vm.pyobject as po
import vm.pyobjectrc as prc
import bytecode.bytecode as bytecode
import vm.builtins.pystr as pystr


FrozenModule = bytecode.FrozenModule["PyConstant"]


@dataclass
class PyConstant(Generic[bytecode.CT]):
    value: ConstantData[bytecode.CT]

    Name: ClassVar = pystr.PyStrRef


@dataclass
class PyObjBag:
    value: VirtualMachine


# TODO: impl ConstantBag for PyObjBag


@po.pyimpl(py_ref=True)
@po.pyclass("code")
@dataclass
class PyCode(po.PyClassImpl, po.TryFromObjectMixin, po.PyValueMixin):
    code: CodeObject[PyConstant]

    def class_(self, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.code_type

    def into_ref(self, vm: VirtualMachine) -> PyRef[PyCode]:
        return prc.PyRef(vm.ctx.types.code_type, None, self)

    # TODO: impl PyRef<PyCode> @ 199

    @pymethod()
    def i__repr__(self) -> str:
        code = self.code
        # FIXME: self should be PyRef[PyCode]
        return f"<code object {code.obj_name} at {self.get_id()} file {code.source_path.as_str()}, line {code.first_line_number}>"


def init(ctx: PyContext) -> None:
    PyCode.extend_class(ctx, ctx.types.code_type)
