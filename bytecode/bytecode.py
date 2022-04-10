from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import ClassVar, Generic, Optional, Protocol, Type, TypeVar, TYPE_CHECKING

if TYPE_CHECKING:
    from bytecode.instruction import Instruction, Label


@dataclass
class Location:
    row: int
    column: int


CT = TypeVar(
    "CT", int, tuple, float, complex, bool, str, bytes, None, type(...), "CodeObject"
)


@dataclass(unsafe_hash=True)
class ConstantData(Generic[CT]):
    value: CT

    def __eq__(self, rhs: ConstantData) -> bool:
        return type(self.value) == type(rhs.value) and self.value == rhs.value


@dataclass
class BasicBag:
    def make_constant(self, constant: ConstantData) -> ConstantData:
        return constant

    def make_name(self, name: str) -> str:
        return name


class ConstantProtocol(Protocol):
    Name: ClassVar[Type]


C = TypeVar("C", bound=ConstantProtocol)


@dataclass
class CodeObject(Generic[C]):
    instructions: list[Instruction]
    locations: list[Location]
    flags: CodeFlags
    posonlyarg_count: int
    arg_count: int
    kwonlyarg_count: int
    source_path: C.Name  # type: ignore
    first_line_number: int
    max_stacksize: int
    obj_name: C.Name  # type: ignore
    cell2arg: Optional[list[int]]
    constants: list[C]
    names: list[C.Name]  # type: ignore
    varnames: list[C.Name]  # type: ignore
    cellvars: list[C.Name]  # type: ignore
    freevars: list[C.Name]  # type: ignore

    def arg_names(self) -> Arguments:
        varargpos = self.arg_count + self.kwonlyarg_count
        posonlyargs = self.varnames[: self.posonlyarg_count]
        args = self.varnames[: self.arg_count]
        kwonlyargs = self.varnames[self.arg_count : varargpos]
        vararg = None
        if CodeFlags.HAS_VARARGS in self.flags:
            vararg = self.varnames[varargpos]
            varargpos += 1
        varkwarg = None
        if CodeFlags.HAS_VARKEYWORDS in self.flags:
            varkwarg = self.varnames[varargpos]
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
class FrozenModule(Generic[C]):
    code: CodeObject[C]
    package: bool
