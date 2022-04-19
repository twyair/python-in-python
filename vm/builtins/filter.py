from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING
from common.error import unreachable


if TYPE_CHECKING:
    from vm.builtins.pytype import PyTypeRef
    from vm.pyobject import PyContext
    from vm.pyobjectrc import PyObjectRef, PyRef
    from protocol.iter import PyIter
    from vm.vm import VirtualMachine
import vm.function_ as fn
import vm.pyobject as po
import vm.types.slot as slot
import vm.protocol.iter as protocol_iter


@po.tp_flags(basetype=True)
@po.pyimpl(iter_next=True, constructor=True)
@po.pyclass("filter")
@dataclass
class PyFilter(
    po.PyClassImpl,
    slot.IterNextMixin,
    slot.IterNextIterableMixin,
    slot.ConstructorMixin,
):
    predicate: PyObjectRef
    iterator: PyIter

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.filter_type

    @classmethod
    def py_new(
        cls, class_: PyTypeRef, fargs: fn.FuncArgs, /, vm: VirtualMachine
    ) -> PyObjectRef:
        args = fargs.bind(__py_new).arguments
        return PyFilter(
            predicate=args["predicate"], iterator=args["iterator"]
        ).into_pyresult_with_type(vm, class_)

    @classmethod
    def next(
        cls, zelf: PyRef[PyFilter], vm: VirtualMachine
    ) -> protocol_iter.PyIterReturn:
        predicate = zelf._.predicate
        while 1:
            v = zelf._.iterator.next(vm)
            if isinstance(v, protocol_iter.PyIterReturnReturn):
                next_obj = v.value
            elif isinstance(v, protocol_iter.PyIterReturnStopIteration):
                return v
            else:
                unreachable()
            predicate_value: PyObjectRef
            if vm.is_none(predicate):
                predicate_value = next_obj
            else:
                r = protocol_iter.PyIterReturn.from_pyresult(
                    lambda: vm.invoke(predicate, fn.FuncArgs([next_obj])), vm
                )
                if isinstance(r, protocol_iter.PyIterReturnReturn):
                    predicate_value = r.value
                elif isinstance(r, protocol_iter.PyIterReturnStopIteration):
                    return r
                else:
                    unreachable()

            if predicate_value.try_to_bool(vm):
                return protocol_iter.PyIterReturnReturn(next_obj)
        unreachable()


def __py_new(predicate, iterator, /):
    ...


def init(context: PyContext) -> None:
    PyFilter.extend_class(context, context.types.filter_type)
