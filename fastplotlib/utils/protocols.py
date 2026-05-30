from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable


ARRAY_LIKE_ATTRS = [
    "dtype",
    "shape",
    "ndim",
    "__getitem__",
]


@runtime_checkable
class ArrayProtocol(Protocol):
    """an object that is sufficiently array-like for lazy loading"""
    @property
    def dtype(self) -> Any: ...

    @property
    def ndim(self) -> int: ...

    @property
    def shape(self) -> tuple[int, ...]: ...

    def __getitem__(self, key) -> ArrayProtocol: ...


@runtime_checkable
class CudaArrayProtocol(Protocol):
    """an object that can be converted to a cupy array"""

    def __cuda_array_interface__(self) -> CudaArrayProtocol: ...


@runtime_checkable
class FutureProtocol(Protocol):
    """An object that is sufficiently Future-like"""

    def cancel(self): ...

    def cancelled(self): ...

    def running(self): ...

    def done(self): ...

    def add_done_callback(self, fn: Callable): ...

    def result(self, timeout: float | None): ...

    def exception(self, timeout: float | None): ...

    def set_result(self, array: ArrayProtocol): ...

    def set_exception(self, exception): ...
