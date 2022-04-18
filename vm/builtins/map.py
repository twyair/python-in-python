from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from vm.builtins.pytype import PyTypeRef
    from vm.pyobject import PyContext
    from vm.pyobjectrc import PyObjectRef, PyRef
    from protocol.iter import PyIter
    from vm.vm import VirtualMachine

    # from vm.function_ import FuncArgs

import vm.pyobject as po
import vm.types.slot as slot
import vm.protocol.iter as protocol_iter
import vm.function_ as fn

from common.error import unreachable


@po.tp_flags(basetype=True)
@po.pyimpl(constructor=True, iter_next=True)
@po.pyclass("map")
@dataclass
class PyMap(
    po.PyClassImpl,
    po.PyValueMixin,
    slot.ConstructorMixin,
    slot.IterNextIterableMixin,
    slot.IterNextMixin,
):
    mapper: PyObjectRef
    iterators: list[PyIter]

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.map_type

    @classmethod
    def py_new(
        cls, class_: PyTypeRef, fargs: fn.FuncArgs, /, vm: VirtualMachine
    ) -> PyObjectRef:
        args = fargs.bind(__py_new).arguments
        return PyMap(
            mapper=args["mapper"], iterators=list(args["iterators"])
        ).into_pyresult_with_type(vm, class_)

    @classmethod
    def next(cls, zelf: PyRef[PyMap], vm: VirtualMachine) -> protocol_iter.PyIterReturn:
        next_objs = []
        for iterator in zelf._.iterators:
            v = iterator.next(vm)
            if isinstance(v, protocol_iter.PyIterReturnReturn):
                item = v.value
            elif isinstance(v, protocol_iter.PyIterReturnStopIteration):
                return v
            else:
                unreachable()
            next_objs.append(item)
        return protocol_iter.PyIterReturn.from_pyresult(
            lambda: vm.invoke(zelf._.mapper, fn.FuncArgs(next_objs)), vm
        )


def __py_new(mapper, /, *iterators):
    ...


def init(context: PyContext) -> None:
    PyMap.extend_class(context, context.types.map_type)
