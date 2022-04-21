from __future__ import annotations
from abc import abstractmethod, ABC

import enum
from dataclasses import dataclass
from typing import (
    Any,
    ClassVar,
    Generic,
    Optional,
    Protocol,
    Type,
    TypeVar,
    TYPE_CHECKING,
    Union,
)

from vm.builtins.pystr import PyStrRef


if TYPE_CHECKING:
    from bytecode.instruction import Instruction, Label
    from vm.vm import VirtualMachine
    from vm.pyobjectrc import PyObjectRef
    from vm.builtins.pystr import PyStrRef
    from vm.builtins.code import PyConstant


@dataclass
class Location:
    row: int
    column: int


@dataclass
class ConstantData(ABC):
    def __eq__(self, rhs: ConstantData) -> bool:
        assert (
            isinstance(self, UnionConstantData)
            and not isinstance(self, (ConstantDataNone, ConstantDataEllipsis))
            and isinstance(rhs, UnionConstantData)
            and not isinstance(rhs, (ConstantDataNone, ConstantDataEllipsis))
        )
        if type(self) != type(rhs):
            return False
        return self.value == rhs.value

    @abstractmethod
    def to_pyobj(self, vm: VirtualMachine) -> PyObjectRef:
        ...

    # TODO: types
    def map_constant(self, bag: Any) -> Any:
        return bag.make_constant(self)


@dataclass
class ConstantDataTuple(ConstantData):
    value: tuple[ConstantData]

    def to_pyobj(self, vm: VirtualMachine) -> PyObjectRef:
        return vm.ctx.new_tuple([x.to_pyobj(vm) for x in self.value])


@dataclass
class ConstantDataInteger(ConstantData):
    value: int

    def to_pyobj(self, vm: VirtualMachine) -> PyObjectRef:
        return vm.ctx.new_int(self.value)


@dataclass
class ConstantDataFloat(ConstantData):
    value: float

    def to_pyobj(self, vm: VirtualMachine) -> PyObjectRef:
        return vm.ctx.new_float(self.value)


@dataclass
class ConstantDataComplex(ConstantData):
    value: complex

    def to_pyobj(self, vm: VirtualMachine) -> PyObjectRef:
        return vm.ctx.new_complex(self.value)


@dataclass
class ConstantDataBoolean(ConstantData):
    value: bool

    def to_pyobj(self, vm: VirtualMachine) -> PyObjectRef:
        return vm.ctx.new_bool(self.value)


@dataclass
class ConstantDataStr(ConstantData):
    value: str

    def to_pyobj(self, vm: VirtualMachine) -> PyObjectRef:
        return vm.ctx.new_str(self.value)


@dataclass
class ConstantDataBytes(ConstantData):
    value: bytes

    def to_pyobj(self, vm: VirtualMachine) -> PyObjectRef:
        return vm.ctx.new_bytes(self.value)


@dataclass
class ConstantDataCode(ConstantData):
    value: CodeObject[ConstantData, str]

    def to_pyobj(self, vm: VirtualMachine) -> PyObjectRef:
        return vm.new_code(self.value)


@dataclass
class ConstantDataNone(ConstantData):
    def to_pyobj(self, vm: VirtualMachine) -> PyObjectRef:
        return vm.ctx.get_none()


@dataclass
class ConstantDataEllipsis(ConstantData):
    def to_pyobj(self, vm: VirtualMachine) -> PyObjectRef:
        return vm.ctx.get_ellipsis()


UnionConstantData = Union[
    ConstantDataBytes,
    ConstantDataBoolean,
    ConstantDataCode,
    ConstantDataComplex,
    ConstantDataEllipsis,
    ConstantDataFloat,
    ConstantDataInteger,
    ConstantDataNone,
    ConstantDataStr,
    ConstantDataTuple,
]


@dataclass
class BasicBag:
    def make_constant(self, constant: ConstantData) -> ConstantData:
        return constant

    def make_name(self, name: str) -> str:
        return name


# class ConstantProtocol(Protocol):
#     Name: ClassVar[Type]


C = TypeVar("C", "PyConstant", ConstantData)
NA = TypeVar("NA", str, "PyStrRef")


@dataclass
class CodeObject(Generic[C, NA]):
    instructions: list[Instruction]
    locations: list[Location]
    flags: CodeFlags
    posonlyarg_count: int
    arg_count: int
    kwonlyarg_count: int
    source_path: NA
    first_line_number: int
    max_stacksize: int
    obj_name: NA
    cell2arg: Optional[list[int]]
    constants: list[C]
    names: list[NA]
    varnames: list[NA]
    cellvars: list[NA]
    freevars: list[NA]

    def arg_names(self) -> Arguments:
        varnames = [x if isinstance(x, str) else x._.as_str() for x in self.varnames]
        varargpos = self.arg_count + self.kwonlyarg_count
        posonlyargs = varnames[: self.posonlyarg_count]
        args = varnames[: self.arg_count]
        kwonlyargs = varnames[self.arg_count : varargpos]
        vararg = None
        if CodeFlags.HAS_VARARGS in self.flags:
            vararg = varnames[varargpos]
            varargpos += 1
        varkwarg = None
        if CodeFlags.HAS_VARKEYWORDS in self.flags:
            varkwarg = varnames[varargpos]
        return Arguments(
            posonlyargs=posonlyargs,
            args=args,
            vararg=vararg,
            kwonlyargs=kwonlyargs,
            varkwarg=varkwarg,
        )

    def label_targets(self) -> set[Label]:
        targets = set()
        for instruction in self.instructions:
            if (l := instruction.label_arg()) is not None:
                targets.add(l)
        return targets

    # TODO: types
    def map_bag(self, bag: Any) -> CodeObject[Any, Any]:
        def map_names(names: list[NA]) -> list[Any]:
            return [map_name(x, bag) for x in names]

        return CodeObject(
            constants=[x.map_constant(bag) for x in self.constants],
            names=map_names(self.names),
            varnames=map_names(self.varnames),
            cellvars=map_names(self.cellvars),
            freevars=map_names(self.freevars),
            source_path=map_name(self.source_path, bag),
            obj_name=map_name(self.obj_name, bag),
            instructions=self.instructions,
            locations=self.locations,
            flags=self.flags,
            posonlyarg_count=self.posonlyarg_count,
            arg_count=self.arg_count,
            kwonlyarg_count=self.kwonlyarg_count,
            first_line_number=self.first_line_number,
            max_stacksize=self.max_stacksize,
            cell2arg=self.cell2arg,
        )


# TODO: types
def map_name(name: Any, bag: Any) -> Any:
    return bag.make_name(name)


class CodeFlags(enum.Flag):
    EMPTY = 0
    NEW_LOCALS = enum.auto()
    IS_GENERATOR = enum.auto()
    IS_COROUTINE = enum.auto()
    HAS_VARARGS = enum.auto()
    HAS_VARKEYWORDS = enum.auto()
    IS_OPTIMIZED = enum.auto()


class ConversionFlag(enum.Enum):
    NONE = enum.auto()
    STR = enum.auto()
    ASCII = enum.auto()
    REPR = enum.auto()


class RaiseKind(enum.Enum):
    RERAISE = enum.auto()
    RAISE = enum.auto()
    RAISE_CAUSE = enum.auto()


@dataclass
class Arguments:
    posonlyargs: list[str]
    args: list[str]
    vararg: Optional[str]
    kwonlyargs: list[str]
    varkwarg: Optional[str]


@dataclass
class FrozenModule(Generic[C, NA]):
    code: CodeObject[C, NA]
    package: bool
