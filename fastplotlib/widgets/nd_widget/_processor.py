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
            data: ArrayProtocol,
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


class NDImageProcessor(NDProcessor):
    @property
    def n_display_dims(self) -> Literal[2, 3]:
        pass

    def _validate_n_display_dims(self, n_display_dims):
        if n_display_dims not in (2, 3):
            raise ValueError("`n_display_dims` must be")


class NDTimeSeriesProcessor(NDProcessor):
    def __init__(
            self,
            data: ArrayProtocol,
            graphic: Literal["line", "heatmap"] = "line",
            n_display_dims: Literal[2, 3] = 2,
            slider_index_maps: tuple[Callable[[Any], int] | None, ...] | None = None,
            display_window: int | float | None = None,
            window_funcs: tuple[WindowFuncCallable | None] | None = None,
            window_sizes: tuple[int | None] | None = None,
            spatial_func: Callable[[ArrayProtocol], ArrayProtocol] | None = None,
    ):
        super().__init__(
            data=data,
            n_display_dims=n_display_dims,
            slider_index_maps=slider_index_maps,
        )

        self._display_window = display_window

    def _validate_data(self, data: ArrayProtocol):
        data = super()._validate_data(data)

        # need to make shape be [n_lines, n_datapoints, 2]
        # this will work for displaying a linestack and heatmap
        # for heatmap just slice: [..., 1]
        # TODO: Think about how to allow n-dimensional lines,
        #  maybe [d1, d2, ..., d(n - 1), n_lines, n_datapoint, 2]
        #  and dn is the x-axis values??
        if data.ndim == 1:
            pass

    @property
    def display_window(self) -> int | float | None:
        """display window in the reference units along the x-axis"""
        return self._display_window

    def __getitem__(self, indices: tuple[Any, ...]) -> ArrayProtocol:
        if self.display_window is not None:
            # map reference units -> array int indices if necessary
            if self.slider_index_maps is not None:
                indices_window = self.slider_index_maps(self.display_window)
            else:
                indices_window = self.display_window

            # half window size
            hw = indices_window // 2

            # for now assume just a single index provided that indicates x axis value
            start = max(indices - hw, 0)
            stop = indices + hw

            # slice dim would be ndim - 1

            return self.data[start:stop]
