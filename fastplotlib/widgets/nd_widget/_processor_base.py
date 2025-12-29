import inspect
from typing import Literal, Callable, Any
from warnings import warn

import numpy as np
from numpy.typing import ArrayLike

from ...utils import subsample_array, ArrayProtocol


# must take arguments: array-like, `axis`: int, `keepdims`: bool
WindowFuncCallable = Callable[[ArrayLike, int, bool], ArrayLike]


class NDProcessor:
    def __init__(
        self,
        data,
        n_display_dims: Literal[2, 3] = 2,
        slider_index_maps: tuple[Callable[[Any], int] | None, ...] | None = None,
        window_funcs: tuple[WindowFuncCallable | None] | None = None,
        window_sizes: tuple[int | None] | None = None,
        spatial_func: Callable[[ArrayProtocol], ArrayProtocol] | None = None,
    ):
        self._data = self._validate_data(data)
        self._slider_index_maps = self._validate_slider_index_maps(slider_index_maps)

    @property
    def data(self) -> ArrayProtocol:
        return self._data

    @data.setter
    def data(self, data: ArrayProtocol):
        self._data = self._validate_data(data)

    def _validate_data(self, data: ArrayProtocol):
        if not isinstance(data, ArrayProtocol):
            raise TypeError("`data` must implement the ArrayProtocol")

        return data

    @property
    def window_funcs(self) -> tuple[WindowFuncCallable | None] | None:
        pass

    @property
    def window_sizes(self) -> tuple[int | None] | None:
        pass

    @property
    def spatial_func(self) -> Callable[[ArrayProtocol], ArrayProtocol] | None:
        pass

    @property
    def slider_dims(self) -> tuple[int, ...] | None:
        pass

    @property
    def slider_index_maps(self) -> tuple[Callable[[Any], int] | None, ...]:
        return self._slider_index_maps

    @slider_index_maps.setter
    def slider_index_maps(self, maps):
        self._maps = self._validate_slider_index_maps(maps)

    def _validate_slider_index_maps(self, maps):
        if maps is not None:
            if not all([callable(m) or m is None for m in maps]):
                raise TypeError

        return maps

    def __getitem__(self, item: tuple[Any, ...]) -> ArrayProtocol:
        pass
