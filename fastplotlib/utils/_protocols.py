from typing import Protocol, runtime_checkable


ARRAY_LIKE_ATTRS = ["shape", "ndim", "__getitem__"]


@runtime_checkable
class ArrayProtocol(Protocol):
    @property
    def ndim(self) -> int: ...

    @property
    def shape(self) -> tuple[int, ...]: ...

    def __getitem__(self, key): ...
