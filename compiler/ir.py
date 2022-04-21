from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import TYPE_CHECKING, Generic, Iterable, Optional, TypeVar

if TYPE_CHECKING:
    from vm.builtins.code import PyConstant

from bytecode import instruction
from bytecode.bytecode import (
    CodeFlags,
    CodeObject,
    ConstantData,
)
from bytecode.instruction import Instruction
from indexset import IndexSet

from compiler.symboltable import Location

BlockIdx = instruction.Label
MAX_LABEL = instruction.Label(1 << 32)


@dataclass
class InstructionInfo:
    instr: Instruction
    location: Optional[Location]


@dataclass
class Block:
    instructions: list[InstructionInfo] = dataclasses.field(default_factory=list)
    next: BlockIdx = MAX_LABEL


@dataclass
class CodeInfo:
    flags: CodeFlags
    posonlyarg_count: int
    arg_count: int
    kwonlyarg_count: int
    source_path: str
    first_line_number: int
    obj_name: str
    blocks: list[Block]
    current_block: BlockIdx
    constants: IndexSet[ConstantData]
    name_cache: IndexSet[str]
    varname_cache: IndexSet[str]
    cellvar_cache: IndexSet[str]
    freevar_cache: IndexSet[str]

    def max_stacksize(self) -> int:
        maxdepth = 0
        stack: list[instruction.Label] = []
        startdepths = [MAX_LABEL.value] * len(self.blocks)
        startdepths[0] = 0
        stack.append(instruction.Label(0))
        # debug = False

        while stack:
            block = stack.pop()
            depth = startdepths[block.value]
            block = self.blocks[block.value]
            for i in block.instructions:
                instr = i.instr
                effect = instr.stack_effect(False)
                new_depth = add_ui(depth, effect)
                if new_depth > maxdepth:
                    maxdepth = new_depth

                jump_label = instr.label_arg()
                if jump_label is not None and not isinstance(
                    instr, instruction.Continue
                ):
                    effect = instr.stack_effect(True)
                    target_depth = add_ui(depth, effect)
                    if target_depth > maxdepth:
                        maxdepth = target_depth
                    stackdepth_push(stack, startdepths, jump_label, target_depth)
                depth = new_depth
                if instr.unconditional_branch():
                    break
            else:
                stackdepth_push(stack, startdepths, block.next, depth)

        return maxdepth

    def cell2arg(self) -> Optional[list[int]]:
        if not self.cellvar_cache:
            return None

        total_args = (
            self.arg_count
            + self.kwonlyarg_count
            + (CodeFlags.HAS_VARARGS in self.flags)
            + (CodeFlags.HAS_VARKEYWORDS in self.flags)
        )

        found_cellarg = False
        cell2arg = []
        for var in self.cellvar_cache:
            idx = self.varname_cache.get_index_of(var)
            if idx is not None and idx < total_args:
                found_cellarg = True
            else:
                idx = -1
            cell2arg.append(idx)

        if found_cellarg:
            return cell2arg
        return None

    def dce(self) -> None:
        for block in self.blocks:
            last_instr = None
            for i, ins in enumerate(block.instructions):
                if ins.instr.unconditional_branch():
                    last_instr = i
                    break
            if last_instr is not None:
                del block.instructions[last_instr + 1 :]

    def finalize_code(self, optimize: int) -> CodeObject[ConstantData, str]:
        max_stacksize = self.max_stacksize()
        cell2arg = self.cell2arg()
        if optimize > 0:
            self.dce()

        num_instructions = 0
        block_to_offset = [instruction.Label(0) for _ in range(len(self.blocks))]

        for idx, block in iter_blocks(self.blocks):
            block_to_offset[idx.value] = instruction.Label(num_instructions)
            num_instructions += len(block.instructions)

        instructions = []
        locations = []

        for _, block in iter_blocks(self.blocks):
            for info in block.instructions:
                instr = info.instr
                if (l := instr.label_arg()) is not None:
                    l.value = block_to_offset[l.value].value
                instructions.append(instr)
                locations.append(info.location)

        return CodeObject(
            flags=self.flags,
            posonlyarg_count=self.posonlyarg_count,
            arg_count=self.arg_count,
            kwonlyarg_count=self.kwonlyarg_count,
            source_path=self.source_path,
            first_line_number=self.first_line_number,
            obj_name=self.obj_name,
            max_stacksize=max_stacksize,
            instructions=instructions,
            locations=locations,
            constants=list(self.constants),
            names=list(self.name_cache),
            varnames=list(self.varname_cache),
            cellvars=list(self.cellvar_cache),
            freevars=list(self.freevar_cache),
            cell2arg=cell2arg,
        )


def iter_blocks(blocks: list[Block]) -> Iterable[tuple[BlockIdx, Block]]:
    def get_idx(i: BlockIdx) -> Optional[tuple[BlockIdx, Block]]:
        if i.value < len(blocks):
            return (i, blocks[i.value])
        return None

    r = get_idx(instruction.Label(0))
    while r is not None:
        yield r
        r = get_idx(r[1].next)


def stackdepth_push(
    stack: list[instruction.Label],
    startdepths: list[int],
    target: instruction.Label,
    depth: int,
) -> None:
    block_depth = startdepths[target.value]
    if block_depth == MAX_LABEL.value or depth > block_depth:
        startdepths[target.value] = depth
        stack.append(target)


def add_ui(a: int, b: int) -> int:
    return a + b
