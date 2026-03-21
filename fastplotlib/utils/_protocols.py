from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


ARRAY_LIKE_ATTRS = [
    "__array__",
    "__array_ufunc__",
    "dtype",
    "shape",
    "ndim",
    "__getitem__",
]


@runtime_checkable
class ArrayProtocol(Protocol):
    def __array__(self) -> ArrayProtocol: ...

    def __array_ufunc__(self, ufunc, method, *inputs, **kwargs): ...

    def __array_function__(self, func, types, *args, **kwargs): ...

    @property
    def dtype(self) -> Any: ...

    @property
    def ndim(self) -> int: ...

    @property
    def shape(self) -> tuple[int, ...]: ...

    def __getitem__(self, key): ...
