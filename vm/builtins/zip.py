from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional
from common.deco import pymethod
from common.error import PyImplBase, unreachable

if TYPE_CHECKING:
    from vm.pyobject import PyContext
    from protocol.iter import PyIter
    from vm.vm import VirtualMachine
    from vm.pyobjectrc import PyRef, PyObjectRef
    from vm.builtins.pytype import PyTypeRef
import vm.pyobject as po
import vm.types.slot as slot
import vm.function_ as fn
import vm.protocol.iter as protocol_iter


@po.tp_flags(basetype=True)
@po.pyimpl(iter_next=True, constructor=True)
@po.pyclass("zip")
@dataclass
class PyZip(
    po.PyClassImpl,
    slot.IterNextIterableMixin,
    slot.IterNextMixin,
    slot.ConstructorMixin,
):
    iterators: list[PyIter]
    strict: bool

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.zip_type

    @pymethod(True)
    @staticmethod
    def i__reduce__(zelf: PyRef[PyZip], *, vm: VirtualMachine) -> PyObjectRef:
        cls = zelf.clone_class()
        tuple_iter = vm.ctx.new_tuple([x.into_object() for x in zelf._.iterators])
        if zelf._.strict:
            return vm.ctx.new_tuple([cls, tuple_iter, vm.ctx.new_bool(True)])
        else:
            return vm.ctx.new_tuple([cls, tuple_iter])

    @pymethod(True)
    @staticmethod
    def i__setstate__(
        zelf: PyRef[PyZip], state: PyObjectRef, /, *, vm: VirtualMachine
    ) -> None:
        try:
            zelf._.strict = state.try_to_bool(vm)
        except PyImplBase as _:
            return None

    @classmethod
    def py_new(
        cls, class_: PyTypeRef, fargs: fn.FuncArgs, /, vm: VirtualMachine
    ) -> PyObjectRef:
        args = fargs.bind(__py_new_args).arguments
        return PyZip(list(args["iterators"]), args["strict"]).into_pyresult_with_type(
            vm, class_
        )

    @classmethod
    def next(cls, zelf: PyRef[PyZip], vm: VirtualMachine) -> protocol_iter.PyIterReturn:
        if not zelf._.iterators:
            return protocol_iter.PyIterReturnStopIteration(None)
        next_objs = []
        for idx, iterator in enumerate(zelf._.iterators):
            n = iterator.next(vm)
            if isinstance(n, protocol_iter.PyIterReturnReturn):
                item = n.value
            elif isinstance(n, protocol_iter.PyIterReturnStopIteration):
                if zelf._.strict:
                    if idx > 0:
                        plural = " " if idx == 1 else "s 1-"
                        vm.new_value_error(
                            "zip() argument {} is shorter than argument{}{}".format(
                                idx + 1, plural, idx
                            )
                        )
                    for idx, iterator in enumerate(zelf._.iterators[1:]):
                        if isinstance(
                            iterator.next(vm), protocol_iter.PyIterReturnReturn
                        ):
                            plural = " " if idx == 1 else "s 1-"
                            vm.new_value_error(
                                "zip() argument {} is longer than argument{}{}".format(
                                    idx + 2, plural, idx + 1
                                )
                            )
                return n
            else:
                unreachable()
            next_objs.append(item)
        return protocol_iter.PyIterReturnReturn(vm.ctx.new_tuple(next_objs))


def __py_new_args(*iterators: PyIter, strict: Optional[bool] = None):
    ...


def init(context: PyContext) -> None:
    PyZip.extend_class(context, context.types.zip_type)
