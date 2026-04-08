from __future__ import annotations

from collections.abc import Callable
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
    """an object that is sufficiently array-like for xarray and fastplotlib"""
    def __array__(self) -> ArrayProtocol: ...

    def __array_ufunc__(self, ufunc, method, *inputs, **kwargs): ...

    def __array_function__(self, func, types, *args, **kwargs): ...

    @property
    def dtype(self) -> Any: ...

    @property
    def ndim(self) -> int: ...

    @property
    def shape(self) -> tuple[int, ...]: ...

    def __getitem__(self, key) -> ArrayProtocol: ...


@runtime_checkable
class FutureArrayProtocol(ArrayProtocol, Protocol):
    """An Future whose result is an array-like once it is resolved, for xarray compatibility"""
    def cancel(self): ...

    def cancelled(self): ...

    def running(self): ...

    def done(self): ...

    def add_done_callback(self, fn: Callable): ...

    def result(self, timeout: float | None): ...

    def exception(self, timeout: float | None): ...

    def set_result(self, array: ArrayProtocol): ...

    def set_exception(self, exception): ...
