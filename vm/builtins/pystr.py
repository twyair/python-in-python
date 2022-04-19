from __future__ import annotations
from dataclasses import dataclass
from logging.config import fileConfig
from typing import TYPE_CHECKING, ClassVar, Optional, TypeAlias

if TYPE_CHECKING:
    from vm.function_ import FuncArgs
    from vm.builtins.bytes import PyBytesRef
    from vm.builtins.pytype import PyTypeRef
    from vm.pyobject import PyContext
    from vm.pyobjectrc import PyRef, PyObjectRef
    from vm.vm import VirtualMachine
    from vm.builtins.int import PyIntRef
    from vm.builtins.list import PyListRef

import vm.pyobject as po
import vm.pyobjectrc as prc
import vm.types.slot as slot

import vm.builtins.iter as pyiter
import vm.protocol.mapping as mapping
import vm.protocol.sequence as sequence
import vm.function_ as fn

from vm.function.arguments import ArgIterable
from common.hash import PyHash
from common.deco import pymethod, pystaticmethod


@po.tp_flags(basetype=True)
@po.pyimpl(
    constructor=True,
    as_mapping=True,
    as_sequence=True,
    hashable=True,
    comparable=True,
    iterable=True,
)
@po.pyclass("str")
@dataclass
class PyStr(
    po.PyClassImpl,
    slot.HashableMixin,
    slot.AsMappingMixin,
    slot.AsSequenceMixin,
    slot.ComparableMixin,
    slot.IterableMixin,
    slot.ConstructorMixin,
):
    value: str

    MAPPING_METHODS: ClassVar[mapping.PyMappingMethods] = mapping.PyMappingMethods(
        length=lambda m, vm: PyStr.mapping_downcast(m)._._len(),
        subscript=lambda m, needle, vm: PyStr.mapping_downcast(m)._._getitem(
            needle, vm
        ),
        ass_subscript=None,
    )

    SEQUENCE_METHODS: ClassVar[sequence.PySequenceMethods] = sequence.PySequenceMethods(
        length=lambda m, vm: PyStr.sequence_downcast(m)._._len(),
        concat=lambda m, other, vm: PyStr.i__add__(
            PyStr.sequence_downcast(m), other, vm=vm
        ),
        repeat=lambda m, n, vm: PyStr._mul(PyStr.sequence_downcast(m), n, vm),
        item=None,  # TODO #lambda m, i, vm: PyStr.sequence_downcast(m)._.get_item_by_index(vm, i)
        contains=lambda m, needle, vm: PyStr.sequence_downcast(m)._._contains(
            needle, vm
        ),
        ass_item=None,
        inplace_concat=None,
        inplace_repeat=None,
    )

    @staticmethod
    def class_(vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.str_type

    @staticmethod
    def from_str(s: str, ctx: PyContext) -> PyStrRef:
        return PyStr.new_ref(PyStr(s), ctx)
        # return PyStr.new_ref(PyStr(
        #     bytes=s.encode(),
        #     kind=Utf8(0),  # FIXME
        #     hash=None
        # ), ctx)

    def as_str(self) -> str:
        return self.value

    @staticmethod
    def new_ref(s: PyStr, ctx: PyContext) -> PyStrRef:
        return prc.PyRef.new_ref(s, ctx.types.str_type, None)

    def _len(self) -> int:
        return len(self.value)

    @staticmethod
    def _mul(zelf: PyRef[PyStr], n: int, vm: VirtualMachine) -> PyStrRef:
        assert n >= 0, n
        return PyStr.new_ref(PyStr(zelf._.value * n), vm.ctx)

    @classmethod
    def cmp(
        cls,
        zelf: PyRef[PyStr],
        other: prc.PyObject,
        op: slot.PyComparisonOp,
        vm: VirtualMachine,
    ) -> po.PyComparisonValue:
        if (res := op.identical_optimization(zelf, other)) is not None:
            return po.PyComparisonValue(res)
        value = other.downcast_ref(PyStr)
        if value is None:
            return po.PyComparisonValue(None)
        return po.PyComparisonValue(op.eval_(zelf._.as_str(), value._.as_str()))

    @classmethod
    def iter(cls, zelf: PyRef[PyStr], vm: VirtualMachine) -> prc.PyObjectRef:
        return PyStrIterator((pyiter.PositionIterInternal.new(zelf, 0), 0)).into_object(
            vm
        )

    @classmethod
    def as_mapping(
        cls, zelf: PyRef[PyStr], vm: VirtualMachine
    ) -> mapping.PyMappingMethods:
        return cls.MAPPING_METHODS

    @classmethod
    def as_sequence(
        cls, zelf: PyRef[PyStr], vm: VirtualMachine
    ) -> sequence.PySequenceMethods:
        return cls.SEQUENCE_METHODS

    @classmethod
    def py_new(
        cls, class_: PyTypeRef, fargs: FuncArgs, /, vm: VirtualMachine
    ) -> prc.PyObjectRef:
        args = fargs.bind(__str_args)
        object_: Optional[PyObjectRef] = args.arguments["object"]
        encoding: Optional[PyStrRef] = args.arguments["encoding"]
        errors: Optional[PyStrRef] = args.arguments["errors"]

        if object_ is not None:
            if encoding is not None:
                string = vm.state.codec_registry.decode_text(
                    object_, encoding._.as_str(), errors, vm
                )
            else:
                string = object_.str(vm)
        else:
            string = PyStr("").into_ref_with_type(vm, class_)

        if string.class_().is_(class_):
            return string
        else:
            return PyStr(string._.as_str()).into_pyresult_with_type(vm, class_)

    @pymethod(True)
    @staticmethod
    def i__add__(
        zelf: PyRef[PyStr], other: PyObjectRef, *, vm: VirtualMachine
    ) -> PyObjectRef:
        if (value := other.payload_(PyStr)) is not None:
            return PyStr.from_str(zelf._.as_str() + value.as_str(), vm.ctx)
        elif (radd := vm.get_method(other, "__radd__")) is not None:
            return vm.invoke(radd, fn.FuncArgs([zelf]))
        else:
            vm.new_type_error(
                f'can only concatenate str (not "{other.class_()._.name()}") to str'
            )

    @pymethod(True)
    def i__bool__(self, *, vm: VirtualMachine) -> bool:
        return bool(self.value)

    def _contains(self, needle: PyObjectRef, vm: VirtualMachine) -> bool:
        raise NotImplementedError

    @pymethod(True)
    def i__contains__(self, needle: PyObjectRef, /, *, vm: VirtualMachine) -> bool:
        return self._contains(needle, vm)

    def _getitem(self, needle: PyObjectRef, vm: VirtualMachine) -> PyObjectRef:
        raise NotImplementedError

    @pymethod(True)
    def i__getitem__(
        self, needle: PyObjectRef, /, *, vm: VirtualMachine
    ) -> PyObjectRef:
        return self._getitem(needle, vm)

    @classmethod
    def hash(cls, zelf: PyRef[PyStr], vm: VirtualMachine) -> PyHash:
        # FIXME?
        return hash(zelf._.as_str())

    @pymethod(True)
    def i__len__(self, *, vm: VirtualMachine) -> int:
        return len(self.value)

    @pymethod(True)
    def isascii(self, *, vm: VirtualMachine) -> bool:
        return self.value.isascii()

    @pymethod(True)
    def i__sizeof__(self, *, vm: VirtualMachine) -> int:
        return self.value.__sizeof__()

    @pymethod(True)
    @staticmethod
    def i__mul__(
        zelf: PyRef[PyStr], value: PyIntRef, /, *, vm: VirtualMachine
    ) -> PyStrRef:
        i = value._.as_int()
        if i == 1 and zelf.class_().is_(vm.ctx.types.str_type):
            return zelf
        else:
            return PyStr.from_str(zelf._.as_str() * i, vm.ctx)

    @pymethod(True)
    @staticmethod
    def i__rmul__(
        zelf: PyRef[PyStr], value: PyIntRef, /, *, vm: VirtualMachine
    ) -> PyStrRef:
        return PyStr.i__mul__(zelf, value, vm=vm)

    @pymethod(True)
    @staticmethod
    def i__str__(zelf: PyRef[PyStr], *, vm: VirtualMachine) -> PyStrRef:
        return zelf

    @pymethod(True)
    def i__repr__(self, *, vm: VirtualMachine) -> str:
        return repr(self.as_str())

    @pymethod(True)
    def lower(self, *, vm: VirtualMachine) -> str:
        return self.value.lower()

    @pymethod(True)
    def casefold(self, *, vm: VirtualMachine) -> str:
        return self.value.casefold()

    @pymethod(True)
    def upper(self, *, vm: VirtualMachine) -> str:
        return self.value.upper()

    @pymethod(True)
    def capitalize(self, *, vm: VirtualMachine) -> str:
        return self.value.capitalize()

    # TODO: test
    @pymethod(False)
    def split(self, fargs: FuncArgs, *, vm: VirtualMachine) -> PyListRef:
        sep, maxsplit = __split_args_make(fargs)
        return vm.ctx.new_list(
            [PyStr.from_str(s, vm.ctx) for s in self.value.split(sep, maxsplit)]
        )

    @pymethod(False)
    def rsplit(self, fargs: FuncArgs, *, vm: VirtualMachine) -> PyListRef:
        sep, maxsplit = __split_args_make(fargs)
        return vm.ctx.new_list(
            [PyStr.from_str(s, vm.ctx) for s in self.value.rsplit(sep, maxsplit)]
        )

    @pymethod(True)
    def strip(self, chars: Optional[PyStrRef] = None, *, vm: VirtualMachine) -> str:
        return self.as_str().strip(chars._.as_str() if chars is not None else chars)

    @pymethod(True)
    def lstrip(self, chars: Optional[PyStrRef] = None, *, vm: VirtualMachine) -> str:
        return self.as_str().lstrip(chars._.as_str() if chars is not None else chars)

    @pymethod(True)
    def rstrip(self, chars: Optional[PyStrRef] = None, *, vm: VirtualMachine) -> str:
        return self.as_str().rstrip(chars._.as_str() if chars is not None else chars)

    @pymethod(False)
    def endswith(self, fargs: FuncArgs, *, vm: VirtualMachine) -> bool:
        raise NotImplementedError

    @pymethod(False)
    def startswith(self, fargs: FuncArgs, *, vm: VirtualMachine) -> bool:
        raise NotImplementedError

    @pymethod(True)
    def removeprefix(self, pref: PyStrRef, /, *, vm: VirtualMachine) -> str:
        return self.as_str().removeprefix(pref._.as_str())

    @pymethod(True)
    def removesuffix(self, suff: PyStrRef, /, *, vm: VirtualMachine) -> str:
        return self.as_str().removesuffix(suff._.as_str())

    @pymethod(True)
    def isalnum(self, *, vm: VirtualMachine) -> bool:
        return self.as_str().isalnum()

    @pymethod(True)
    def isnumeric(self, *, vm: VirtualMachine) -> bool:
        return self.as_str().isnumeric()

    @pymethod(True)
    def isdigit(self, *, vm: VirtualMachine) -> bool:
        return self.as_str().isdigit()

    @pymethod(True)
    def isdecimal(self, *, vm: VirtualMachine) -> bool:
        return self.as_str().isdecimal()

    @pymethod(True)
    def i__mod__(self, values: PyObjectRef, /, *, vm: VirtualMachine) -> str:
        raise NotImplementedError

    @pymethod(True)
    def i__rmod__(self, values: PyObjectRef, /, *, vm: VirtualMachine) -> PyObjectRef:
        return vm.ctx.get_not_implemented()

    @pymethod(False)
    def format(self, fargs: FuncArgs, *, vm: VirtualMachine) -> str:
        raise NotImplementedError

    @pymethod(True)
    def i__format__(self, spec: PyStrRef, *, vm: VirtualMachine) -> str:
        raise NotImplementedError

    @pymethod(True)
    def title(self, *, vm: VirtualMachine) -> str:
        return self.as_str().title()

    @pymethod(True)
    def swapcase(self, *, vm: VirtualMachine) -> str:
        return self.as_str().swapcase()

    @pymethod(True)
    def isalpha(self, *, vm: VirtualMachine) -> bool:
        return self.as_str().isalpha()

    @pymethod(True)
    def replace(
        self,
        old: PyStrRef,
        new: PyStrRef,
        count: Optional[int] = None,
        /,
        *,
        vm: VirtualMachine,
    ) -> str:
        if count is None:
            count = -1
        return self.as_str().replace(old._.as_str(), new._.as_str(), count)

    @pymethod(True)
    def isprintable(self, *, vm: VirtualMachine) -> bool:
        return self.as_str().isprintable()

    @pymethod(True)
    def isspace(self, *, vm: VirtualMachine) -> bool:
        return self.as_str().isspace()

    @pymethod(True)
    def islower(self, *, vm: VirtualMachine) -> bool:
        return self.as_str().islower()

    @pymethod(True)
    def isupper(self, *, vm: VirtualMachine) -> bool:
        return self.as_str().isupper()

    @pymethod(False)
    def splitlines(self, fargs: FuncArgs, *, vm: VirtualMachine) -> PyListRef:
        raise NotImplementedError

    # TODO: `iterable: ArgIterable[PyStrRef]`
    @pymethod(True)
    def join(self, iterable: ArgIterable, /, *, vm: VirtualMachine) -> str:
        return self.value.join(x.downcast(PyStr)._.as_str() for x in iterable.iter(vm))

    @pymethod(False)
    def find(self, fargs: FuncArgs, *, vm: VirtualMachine) -> int:
        raise NotImplementedError

    @pymethod(False)
    def rfind(self, fargs: FuncArgs, *, vm: VirtualMachine) -> int:
        raise NotImplementedError

    @pymethod(False)
    def index(self, fargs: FuncArgs, *, vm: VirtualMachine) -> int:
        raise NotImplementedError

    @pymethod(False)
    def rindex(self, fargs: FuncArgs, *, vm: VirtualMachine) -> int:
        raise NotImplementedError

    @pymethod(True)
    def partition(self, sep: PyStrRef, *, vm: VirtualMachine) -> PyObjectRef:
        return vm.ctx.new_tuple(
            [vm.ctx.new_str(x) for x in self.value.partition(sep._.as_str())]
        )

    @pymethod(True)
    def rpartition(self, sep: PyStrRef, *, vm: VirtualMachine) -> PyObjectRef:
        return vm.ctx.new_tuple(
            [vm.ctx.new_str(x) for x in self.value.rpartition(sep._.as_str())]
        )

    @pymethod(True)
    def istitle(self, *, vm: VirtualMachine) -> bool:
        return self.as_str().istitle()

    @pymethod(False)
    def count(self, fargs: FuncArgs, *, vm: VirtualMachine) -> int:
        raise NotImplementedError

    @pymethod(True)
    def zfill(self, width: int, /, *, vm: VirtualMachine) -> str:
        return self.as_str().zfill(width)

    @pymethod(True)
    def center(
        self,
        width: int,
        fillchar: Optional[PyStrRef] = None,
        /,
        *,
        vm: VirtualMachine,
    ) -> str:
        return self.value.center(
            width, fillchar._.as_str() if fillchar is not None else " "
        )

    @pymethod(True)
    def ljust(
        self,
        width: int,
        fillchar: Optional[PyStrRef] = None,
        /,
        *,
        vm: VirtualMachine,
    ) -> str:
        return self.value.ljust(
            width, fillchar._.as_str() if fillchar is not None else " "
        )

    @pymethod(True)
    def rjust(
        self,
        width: int,
        fillchar: Optional[PyStrRef] = None,
        /,
        *,
        vm: VirtualMachine,
    ) -> str:
        return self.value.rjust(
            width, fillchar._.as_str() if fillchar is not None else " "
        )

    @pymethod(False)
    def expandtabs(self, fargs: FuncArgs, *, vm: VirtualMachine) -> str:
        raise NotImplementedError

    @pymethod(True)
    def isidentifier(self, *, vm: VirtualMachine) -> bool:
        return self.as_str().isidentifier()

    @pymethod(True)
    def translate(self, table: PyObjectRef, *, vm: VirtualMachine) -> str:
        raise NotImplementedError

    @pystaticmethod(True)
    @staticmethod
    def maketrans(
        dict_or_str: PyObjectRef,
        to_str: Optional[PyStrRef] = None,
        none_str: Optional[PyStrRef] = None,
        *,
        vm: VirtualMachine,
    ) -> PyObjectRef:
        raise NotImplementedError

    @pymethod(False)
    @staticmethod
    def encode(
        zelf: PyRef[PyStr], fargs: FuncArgs, *, vm: VirtualMachine
    ) -> PyBytesRef:
        args = fargs.bind(__encode_args).arguments
        return encode_string(zelf, args["encoding"], args["error"], vm)


# TODO: delete
PyStrRef: TypeAlias = "PyRef[PyStr]"


def __split_args(sep: Optional[PyStrRef] = None, maxsplit: Optional[PyIntRef] = None):
    ...


def __split_args_make(fargs: FuncArgs) -> tuple[str, int]:
    args = fargs.bind(__split_args).arguments
    if (s := args["sep"]) is not None:
        sep = s._.as_str()
    else:
        sep = " "
    if (m := args["maxsplit"]) is not None:
        maxsplit = m._.as_int()
    else:
        maxsplit = -1
    return sep, maxsplit


def __str_args(
    object: Optional[PyObjectRef] = None,
    encoding: Optional[PyStrRef] = None,
    errors: Optional[PyStrRef] = None,
):
    ...


def __encode_args(
    encoding: Optional[PyStrRef] = None, errors: Optional[PyStrRef] = None
):
    ...


@po.pyimpl(constructor=False, iter_next=True)
@po.pyclass("str_iterator")
@dataclass
class PyStrIterator(
    po.PyClassImpl,
    slot.IterNextIterableMixin,
    slot.IterNextMixin,
):
    value: tuple[pyiter.PositionIterInternal[PyStrRef], int]

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.str_iterator_type

    @classmethod
    def next(cls, zelf: PyRef[PyStrIterator], vm: VirtualMachine) -> slot.PyIterReturn:
        raise NotImplementedError


def encode_string(
    s: PyStrRef,
    encoding: Optional[PyStrRef],
    errors: Optional[PyStrRef],
    vm: VirtualMachine,
) -> PyBytesRef:
    raise NotImplementedError


def init(ctx: PyContext) -> None:
    PyStr.extend_class(ctx, ctx.types.str_type)
    PyStrIterator.extend_class(ctx, ctx.types.str_iterator_type)
