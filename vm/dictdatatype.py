from __future__ import annotations
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable, Iterable, Optional

if TYPE_CHECKING:
    from vm.pyobjectrc import PyObjectRef
    from vm.vm import VirtualMachine


@dataclass
class DictContext:
    vm: Optional[VirtualMachine]


@dataclass
class DictKey:
    ctx: DictContext
    value: PyObjectRef
    _hash: Optional[int] = None

    def __hash__(self) -> int:
        if self._hash is None:
            assert self.ctx.vm is not None
            self._hash = self.value.hash(self.ctx.vm)
        return self._hash

    def __eq__(self, other: DictKey) -> bool:
        assert self.ctx.vm is not None
        return self.ctx.vm.identical_or_equal(self.value, other.value)


@dataclass
class DictItem:
    key: PyObjectRef
    value: PyObjectRef


@dataclass
class Dict:
    inner: dict[DictKey, DictItem] = field(default_factory=dict)
    ctx: DictContext = field(default_factory=lambda: DictContext(None))

    def _mk(self, key: PyObjectRef) -> DictKey:
        return DictKey(self.ctx, key)

    def _sw(self, vm: VirtualMachine) -> None:
        self.ctx.vm = vm

    def insert(self, vm: VirtualMachine, key: PyObjectRef, value: PyObjectRef) -> None:
        self._sw(vm)
        self.inner[self._mk(key)] = DictItem(key, value)

    def contains(self, vm: VirtualMachine, key: PyObjectRef) -> bool:
        self._sw(vm)
        return self._mk(key) in self.inner

    def get(self, vm: VirtualMachine, key: PyObjectRef) -> Optional[PyObjectRef]:
        self._sw(vm)
        item = self.inner.get(self._mk(key), None)
        if item is None:
            return None
        return item.value

    def get_chain(
        self, vm: VirtualMachine, other: Dict, key: PyObjectRef
    ) -> Optional[PyObjectRef]:
        self._sw(vm)
        if (x := self.get(vm, key)) is not None:
            return x
        else:
            return other.get(vm, key)

    def clear(self) -> None:
        self.inner.clear()

    def delete(self, vm: VirtualMachine, key: PyObjectRef) -> None:
        self._sw(vm)
        if self.delete_if_exists(vm, key):
            vm.new_key_error(key)

    def delete_if_exists(self, vm: VirtualMachine, key: PyObjectRef) -> bool:
        self._sw(vm)
        return self.inner.pop(self._mk(key), None) is None

    def delete_or_insert(
        self, vm: VirtualMachine, key: PyObjectRef, value: PyObjectRef
    ) -> None:
        self._sw(vm)
        k = self._mk(key)
        if k in self.inner:
            return
        self.inner[k] = DictItem(key, value)

    def setdefault(
        self, vm: VirtualMachine, key: PyObjectRef, default: Callable[[], PyObjectRef]
    ) -> PyObjectRef:
        self._sw(vm)
        item = self.inner.setdefault(self._mk(key), DictItem(key, default()))  # FIXME
        return item.value

    def setdefault_entry(
        self, vm: VirtualMachine, key: PyObjectRef, default: Callable[[], PyObjectRef]
    ) -> tuple[PyObjectRef, PyObjectRef]:
        self._sw(vm)
        item = self.inner.setdefault(self._mk(key), DictItem(key, default()))  # FIXME
        return (item.key, item.value)

    def len(self) -> int:
        return len(self.inner)

    def is_empty(self) -> bool:
        return self.len() == 0

    def keys(self) -> list[PyObjectRef]:
        return [x.value for x in self.inner]

    def values(self) -> list[PyObjectRef]:
        return [x.value for x in self.inner.values()]

    def pop(self, vm: VirtualMachine, key: PyObjectRef) -> Optional[PyObjectRef]:
        self._sw(vm)
        item = self.inner.pop(self._mk(key), None)
        if item is None:
            return None
        return item.value

    def items(self) -> list[tuple[PyObjectRef, PyObjectRef]]:
        return [(item.key, item.value) for item in self.inner.values()]

    def clone(self) -> Dict:
        return Dict(inner=self.inner.copy())
