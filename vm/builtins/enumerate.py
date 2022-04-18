from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional
from common.error import unreachable
from vm.builtins.iter import IterStatusActive

if TYPE_CHECKING:
    from protocol.iter import PyIter
    from vm.builtins.iter import PositionIterInternal
    from vm.builtins.pytype import PyTypeRef
    from vm.pyobject import PyContext
    from vm.pyobjectrc import PyObjectRef, PyRef
    from vm.vm import VirtualMachine
    from vm.builtins.int import PyIntRef
import vm.pyobject as po
import vm.types.slot as slot
import vm.builtins.genericalias as pygenericalias
import vm.function_ as fn
import vm.protocol.iter as protocol_iter
from common.deco import pyclassmethod, pymethod


@po.tp_flags(basetype=True)
@po.pyimpl(iter_next=True, constructor=True)
@po.pyclass("enumerate")
@dataclass
class PyEnumerate(
    po.PyValueMixin,
    po.PyClassImpl,
    po.TryFromObjectMixin,
    slot.ConstructorMixin,
    slot.IterNextMixin,
    slot.IterNextIterableMixin,
):
    counter: int
    iterator: PyIter

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.enumerate_type

    @pyclassmethod(True)
    @staticmethod
    def i__class_getitem__(
        class_: PyTypeRef, args: PyObjectRef, *, vm: VirtualMachine
    ) -> PyRef[pygenericalias.PyGenericAlias]:
        return pygenericalias.PyGenericAlias.new(class_, args, vm).into_ref(vm)

    @pymethod(True)
    @staticmethod
    def i__reduce__(zelf: PyRef[PyEnumerate], *, vm: VirtualMachine) -> PyObjectRef:
        return vm.ctx.new_tuple(
            [
                zelf.clone_class(),
                vm.ctx.new_tuple(
                    [zelf._.iterator.as_ref(), vm.ctx.new_int(zelf._.counter)]
                ),
            ]
        )

    @classmethod
    def py_new(
        cls, class_: PyTypeRef, fargs: fn.FuncArgs, /, vm: VirtualMachine
    ) -> PyObjectRef:
        args = fargs.bind(__py_new_args).arguments
        start: Optional[PyIntRef] = args["start"]
        if start is not None:
            counter = start._.as_int()
        else:
            counter = 0
        return PyEnumerate(counter=counter, iterator=args["iterator"]).into_ref(vm)

    @classmethod
    def next(
        cls, zelf: PyRef[PyEnumerate], vm: VirtualMachine
    ) -> protocol_iter.PyIterReturn:
        v = zelf._.iterator.next(vm)
        if isinstance(v, protocol_iter.PyIterReturnStopIteration):
            return v
        elif isinstance(v, protocol_iter.PyIterReturnReturn):
            next_obj = v.value
        else:
            unreachable()
        position = zelf._.counter
        zelf._.counter += 1
        return protocol_iter.PyIterReturnReturn(
            vm.ctx.new_tuple([vm.ctx.new_int(position), next_obj])
        )


def __py_new_args(iterator: PyIter, start: Optional[PyIntRef]):
    ...


@po.pyimpl(iter_next=True)
@po.pyclass("reversed")
@dataclass
class PyReverseSequenceIterator(
    po.PyValueMixin,
    po.PyClassImpl,
    po.TryFromObjectMixin,
    slot.IterNextMixin,
):
    internal: PositionIterInternal[PyObjectRef]

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.reverse_iter_type

    @staticmethod
    def new(obj: PyObjectRef, len: int) -> PyReverseSequenceIterator:
        return PyReverseSequenceIterator(PositionIterInternal.new(obj, max(len - 1, 0)))

    @pymethod(True)
    def i__length_hint__(self, *, vm: VirtualMachine) -> int:
        if isinstance(self.internal.status, IterStatusActive):
            if self.internal.position <= self.internal.status.value.length(vm):
                return self.internal.position + 1
        return 0

    @pymethod(True)
    def i__setstate__(self, state: PyObjectRef, *, vm: VirtualMachine) -> None:
        self.internal.set_state(state, lambda _, pos: pos, vm)

    @pymethod(True)
    def i__reduce__(self, *, vm: VirtualMachine) -> PyObjectRef:
        return self.internal.builtins_reversed_reduce(lambda x: x.clone(), vm)

    @classmethod
    def next(
        cls, zelf: PyRef[PyReverseSequenceIterator], vm: VirtualMachine
    ) -> protocol_iter.PyIterReturn:
        return zelf._.internal.rev_next(
            lambda obj, pos: protocol_iter.PyIterReturn.from_getitem_result(
                lambda: obj.get_item(vm.ctx.new_int(pos), vm), vm  # FIXME?
            )
        )


def init(context: PyContext) -> None:
    PyEnumerate.extend_class(context, context.types.enumerate_type)
    PyReverseSequenceIterator.extend_class(context, context.types.reverse_iter_type)
