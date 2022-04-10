from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Generic, Iterable, Iterator, Optional, TypeVar

T = TypeVar("T")


@dataclass
class IndexSet(Generic[T]):
    # d: dict[T, int]
    d: list[T]

    @staticmethod
    def new() -> IndexSet[T]:
        return IndexSet([])

    @staticmethod
    def from_seq(values: Iterable[T]) -> IndexSet[T]:
        return IndexSet(list(values))
        # d = {}
        # for i, v in enumerate(values):
        #     d[v] = i
        # return IndexSet(d)

    def insert_full(self, value: T) -> tuple[int, bool]:
        if value in self.d:
            index = self.d.index(value)
            return (index, False)
        index = len(self.d)
        self.d.append(value)
        return (index, True)

    def position(self, predicate: Callable[[T], bool]) -> Optional[int]:
        for i, v in enumerate(self.d):
            if predicate(v):
                return i
        return None

    def get_index_of(self, value: T) -> Optional[int]:
        if value not in self.d:
            return None
        return self.d.index(value)

    def __len__(self) -> int:
        return len(self.d)

    def __iter__(self) -> Iterator[T]:
        return iter(self.d)
