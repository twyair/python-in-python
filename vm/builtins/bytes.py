from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar, Optional, TypeAlias
from common.error import unreachable

if TYPE_CHECKING:
    from vm.builtins.pytype import PyTypeRef
    from vm.pyobject import PyContext
    from vm.pyobjectrc import PyObject, PyObjectRef, PyRef
    from vm.vm import VirtualMachine

import vm.builtins.iter as pyiter
import vm.builtins.slice as pyslice
import vm.function_ as fn
import vm.protocol.iter as protocol_iter
import vm.protocol.mapping as mapping
import vm.protocol.sequence as sequence
import vm.protocol.buffer as buffer
import vm.pyobject as po
import vm.pyobjectrc as prc
import vm.sliceable as sliceable
import vm.types.slot as slot

from common.deco import pyclassmethod, pymethod, pystaticmethod
from common.hash import PyHash


@po.tp_flags(basetype=True)
@po.pyimpl(
    constructor=True,
    as_mapping=True,
    as_sequence=True,
    hashable=True,
    comparable=True,
    as_buffer=True,
    iterable=True,
)
@po.pyclass("bytes")
@dataclass
class PyBytes(
    po.PyClassImpl,
    slot.ConstructorMixin,
    slot.AsMappingMixin,
    slot.AsSequenceMixin,
    slot.HashableMixin,
    slot.ComparableMixin,
    slot.AsBufferMixin,
    slot.IterableMixin,
):
    inner: bytes

    MAPPING_METHODS: ClassVar[mapping.PyMappingMethods] = mapping.PyMappingMethods(
        length=lambda m, vm: PyBytes.mapping_downcast(m)._._len(),
        subscript=lambda m, needle, vm: PyBytes.mapping_downcast(m)._._getitem(
            needle, vm
        ),
        ass_subscript=None,
    )

    SEQUENCE_METHODS: ClassVar[sequence.PySequenceMethods] = sequence.PySequenceMethods(
        length=lambda s, vm: PyBytes.sequence_downcast(s)._._len(),
        concat=lambda s, other, vm: vm.ctx.new_bytes(
            PyBytes.sequence_downcast(s)._._concat(other, vm)
        ),
        repeat=lambda s, n, vm: vm.ctx.new_bytes(
            PyBytes.sequence_downcast(s)._._repeat(n)
        ),
        item=lambda s, i, vm: vm.ctx.new_bytes(
            bytes([PyBytes.sequence_downcast(s)._.get_item_by_index(vm, i)])
        ),
        contains=lambda s, other, vm: PyBytes.sequence_downcast(s)._._contains(
            other, vm
        ),
    )

    def debug_repr(self) -> str:
        return str(self.inner)

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.bytes_type

    @staticmethod
    def new_ref(value: bytes, ctx: PyContext) -> PyBytesRef:
        return prc.PyRef.new_ref(PyBytes(value), ctx.types.bytes_type, None)

    def _concat(self, other: PyObjectRef, vm: VirtualMachine) -> bytes:
        return other.try_bytes_like(vm, lambda v: self.inner + v)

    @pymethod(True)
    def i__repr__(self, *, vm: VirtualMachine) -> str:
        return repr(self.inner)

    def _len(self) -> int:
        return len(self.inner)

    @pymethod(True)
    def i__len__(self, *, vm: VirtualMachine) -> int:
        return self._len()

    # @pymethod(True)
    # def bytes()

    @pymethod(True)
    def i__sizeof__(self, *, vm: VirtualMachine) -> int:
        return self.__sizeof__()

    @pymethod(True)
    def i__add__(self, other: PyObjectRef, *, vm: VirtualMachine) -> bytes:
        arg = fn.ArgBytesLike.try_from_borrowed_object(vm, other)
        return self.inner + arg.value.methods.obj_bytes(arg.value)

    def _contains(self, needle: PyObjectRef, vm: VirtualMachine) -> bool:
        raise NotImplementedError

    @pymethod(True)
    def i__contains__(self, needle: PyObjectRef, *, vm: VirtualMachine) -> bool:
        return self._contains(needle, vm)

    @pystaticmethod(True)
    @staticmethod
    def maketrans(
        frm: PyObjectRef, to: PyObjectRef, *, vm: VirtualMachine
    ) -> PyObjectRef:
        raise NotImplementedError

    def index_in_range(self, i: int) -> bool:
        return not (i >= len(self.inner) or i < 0 and -i > len(self.inner))

    def get_item_by_index_opt(self, index: int) -> Optional[int]:
        if self.index_in_range(index):
            return self.inner[index]
        else:
            return None

    def get_item_by_index(self, vm: VirtualMachine, index: int) -> int:
        v = self.get_item_by_index_opt(index)
        if v is None:
            vm.new_index_error("index out of range")
        return v

    def get_item_by_slice(self, vm: VirtualMachine, s: pyslice.SaturatedSlice) -> bytes:
        return self.inner[s.to_primitive()]

    def _getitem(self, needle: PyObject, vm: VirtualMachine) -> PyObjectRef:
        v = sliceable.SequenceIndex.try_from_borrowed_object(vm, needle)
        if isinstance(v, sliceable.SequenceIndexInt):
            return vm.ctx.new_int(self.get_item_by_index(vm, v.value))
        else:
            return vm.ctx.new_bytes(self.get_item_by_slice(vm, v.value))

    @pymethod(True)
    def i__getitem__(self, needle: PyObjectRef, *, vm: VirtualMachine) -> PyObjectRef:
        return self._getitem(needle, vm)

    @pymethod(True)
    def isalnum(self, *, vm: VirtualMachine) -> bool:
        return self.inner.isalnum()

    @pymethod(True)
    def isalpha(self, *, vm: VirtualMachine) -> bool:
        return self.inner.isalpha()

    @pymethod(True)
    def isascii(self, *, vm: VirtualMachine) -> bool:
        return self.inner.isascii()

    @pymethod(True)
    def isdigit(self, *, vm: VirtualMachine) -> bool:
        return self.inner.isdigit()

    @pymethod(True)
    def islower(self, *, vm: VirtualMachine) -> bool:
        return self.inner.islower()

    @pymethod(True)
    def isspace(self, *, vm: VirtualMachine) -> bool:
        return self.inner.isspace()

    @pymethod(True)
    def isupper(self, *, vm: VirtualMachine) -> bool:
        return self.inner.isupper()

    @pymethod(True)
    def istitle(self, *, vm: VirtualMachine) -> bool:
        return self.inner.istitle()

    @pymethod(True)
    def lower(self, *, vm: VirtualMachine) -> bytes:
        return self.inner.lower()

    @pymethod(True)
    def upper(self, *, vm: VirtualMachine) -> bytes:
        return self.inner.upper()

    @pymethod(True)
    def capitalize(self, *, vm: VirtualMachine) -> bytes:
        return self.inner.capitalize()

    @pymethod(True)
    def swapcase(self, *, vm: VirtualMachine) -> bytes:
        return self.inner.swapcase()

    @pymethod(True)
    def hex(
        self,
        sep: Optional[PyObjectRef] = None,
        bytes_per_sep: Optional[PyObjectRef] = None,
        *,
        vm: VirtualMachine,
    ) -> PyObjectRef:
        raise NotImplementedError

    @pyclassmethod(True)
    @staticmethod
    def fromhex(
        class_: PyTypeRef, string: PyObjectRef, *, vm: VirtualMachine
    ) -> PyObjectRef:
        raise NotImplementedError

    def _repeat(self, n: int, /) -> bytes:
        return self.inner * n

    # TODO: impl PyBytes @ 115

    # TODO:
    # @pymethod(True)
    # def center(self, options: ByteInnerPaddingOptions, *, vm: VirtualMachine)

    @classmethod
    def iter(cls, zelf: PyRef[PyBytes], vm: VirtualMachine) -> PyObjectRef:
        return PyBytesIterator(pyiter.PositionIterInternal.new(zelf, 0)).into_ref(vm)

    @classmethod
    def hash(cls, zelf: PyRef[PyBytes], vm: VirtualMachine) -> PyHash:
        return hash(zelf._.inner)  # FIXME? use hash_secret?

    @classmethod
    def as_mapping(
        cls, zelf: PyRef[PyBytes], vm: VirtualMachine
    ) -> mapping.PyMappingMethods:
        return cls.MAPPING_METHODS

    @classmethod
    def as_sequence(
        cls, zelf: PyRef[PyBytes], vm: VirtualMachine
    ) -> sequence.PySequenceMethods:
        return cls.SEQUENCE_METHODS

    @classmethod
    def py_new(
        cls, class_: PyTypeRef, args: fn.FuncArgs, /, vm: VirtualMachine
    ) -> PyObjectRef:
        raise NotImplementedError

    @classmethod
    def cmp(
        cls,
        zelf: PyRef[PyBytes],
        other: PyObject,
        op: slot.PyComparisonOp,
        vm: VirtualMachine,
    ) -> po.PyComparisonValue:
        if (res := op.identical_optimization(zelf, other)) is not None:
            return po.PyComparisonValue(res)
        elif other.isinstance(vm.ctx.types.memoryview_type) and op not in (
            slot.PyComparisonOp.Eq,
            slot.PyComparisonOp.Ne,
        ):
            vm.new_type_error(
                "'{}' not supported between instances of '{}' and '{}'".format(
                    op.operator_token(), zelf.class_()._.name(), other.class_()._.name()
                )
            )
        else:
            return po.PyComparisonValue(
                other.try_bytes_like(vm, lambda v: op.eval_(zelf._.inner, v))
            )

    @classmethod
    def as_buffer(cls, zelf: PyRef[PyBytes], vm: VirtualMachine) -> buffer.PyBuffer:
        return buffer.PyBuffer(
            zelf, buffer.BufferDescriptor.simple(zelf._._len(), True), BUFFER_METHODS
        )


BUFFER_METHODS = buffer.BufferMethods(
    obj_bytes=lambda buffer: buffer.obj.downcast_unchecked_ref(PyBytes)._.inner,
    obj_bytes_mut=lambda _: unreachable(),
    release=lambda _: None,
    retain=lambda _: None,
)


@po.pyimpl(iter_next=True)
@po.pyclass("bytes_iterator")
@dataclass
class PyBytesIterator(po.PyClassImpl, slot.IterNextMixin, slot.IterNextIterableMixin):
    internal: pyiter.PositionIterInternal[PyBytesRef]

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.bytes_iterator_type

    @pymethod(True)
    def i__length_hint__(self, *, vm: VirtualMachine) -> int:
        return self.internal.length_hint(lambda obj: obj._._len())

    @pymethod(True)
    def i__reduce__(self, *, vm: VirtualMachine) -> PyObjectRef:
        return self.internal.builtins_iter_reduce(lambda x: x, vm)

    @pymethod(True)
    def i__setstate__(self, state: PyObjectRef, /, *, vm: VirtualMachine) -> None:
        self.internal.set_state(state, lambda obj, pos: min(obj._._len(), pos), vm)

    @classmethod
    def next(
        cls, zelf: PyRef[PyBytesIterator], vm: VirtualMachine
    ) -> protocol_iter.PyIterReturn:
        def get(obj: PyBytesRef, pos: int) -> protocol_iter.PyIterReturn:
            v = obj._.get_item_by_index_opt(pos)
            return protocol_iter.PyIterReturn.from_option(
                vm.ctx.new_int(v) if v is not None else None
            )

        return zelf._.internal.next(get)


PyBytesRef: TypeAlias = "PyRef[PyBytes]"


def init(context: PyContext) -> None:
    PyBytes.extend_class(context, context.types.bytes_type)
    PyBytesIterator.extend_class(context, context.types.bytes_iterator_type)
