from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING
from common.deco import pymethod

if TYPE_CHECKING:
    from vm.builtins.pytype import PyTypeRef
    from vm.pyobject import PyContext
    from vm.pyobjectrc import PyObjectRef, PyRef
    from vm.vm import VirtualMachine
import vm.pyobject as po
import vm.pyobjectrc as prc
import vm.function_ as fn
import vm.types.slot as slot
import vm.builtins.dict as pydict


@po.tp_flags(basetype=True, has_dict=True)
@po.pyimpl(constructor=True, comparable=True)
@po.pyclass("SimpleNamespace")
@dataclass
class PyNamespace(
    po.PyClassImpl,
    slot.ConstructorMixin,
    slot.ComparableMixin,
):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.namespace_type

    @staticmethod
    def new_ref(ctx: PyContext) -> PyRef[PyNamespace]:
        return prc.PyRef.new_ref(
            PyNamespace(), ctx.types.namespace_type, ctx.new_dict()
        )

    @pymethod(False)
    @staticmethod
    def i__init__(
        zelf: PyRef[PyNamespace], args: fn.FuncArgs, *, vm: VirtualMachine
    ) -> None:
        if args.args:
            vm.new_type_error("no positional arguments expected")
        for name, value in args.kwargs.items():
            zelf.set_attr(vm.ctx.new_str(name), value, vm)

    @pymethod(True)
    @staticmethod
    def i__repr__(zelf: PyRef[PyNamespace], *, vm: VirtualMachine) -> str:
        if zelf.class_().is_(vm.ctx.types.namespace_type):
            name = "namespace"
        else:
            name = zelf.class_()._.slot_name()

        raise NotImplementedError

    @classmethod
    def py_new(
        cls, class_: PyTypeRef, fargs: fn.FuncArgs, /, vm: VirtualMachine
    ) -> PyObjectRef:
        _ = fargs.bind(__py_new_args)
        return PyNamespace().into_pyresult_with_type(vm, class_)

    @classmethod
    def cmp(
        cls,
        zelf: PyRef[PyNamespace],
        other: PyObjectRef,
        op: slot.PyComparisonOp,
        vm: VirtualMachine,
    ) -> po.PyComparisonValue:
        value = other.downcast_ref(PyNamespace)
        if value is None:
            return po.PyComparisonValue(None)
        d1 = zelf.dict_()
        d2 = value.dict_()
        assert d1 is not None
        assert d2 is not None
        return pydict.PyDict.cmp(d1, d2, op, vm)


def __py_new_args():
    ...


def init(context: PyContext) -> None:
    return PyNamespace.extend_class(context, context.types.namespace_type)
