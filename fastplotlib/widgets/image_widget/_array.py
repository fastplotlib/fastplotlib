import numpy as np
from numpy.typing import NDArray
from typing import Literal, Callable


class ImageWidgetArray:
    def __init__(
            self,
            data: NDArray,
            window_functions: dict = None,
            frame_apply: Callable = None,
            display_dims: Literal[2, 3] = 2,
            dim_names: str = "tzxy",
    ):
        self._data = data
        self._window_functions = window_functions
        self._frame_apply = frame_apply
        self._dim_names = dim_names

        for k in self._window_functions:
            if k not in dim_names:
                raise KeyError

        self._display_dims = display_dims

    @property
    def data(self) -> NDArray:
        return self._data

    @data.setter
    def data(self, data: NDArray):
        self._data = data

    @property
    def window_functions(self) -> dict | None:
        return self._window_functions

    @window_functions.setter
    def window_functions(self, wf: dict | None):
        self._window_functions = wf

    @property
    def frame_apply(self, fa: Callable | None):
        self._frame_apply = fa

    @frame_apply.setter
    def frame_apply(self) -> Callable | None:
        return self._frame_apply

    def _apply_window_functions(self, array: NDArray, key):
        if self.window_functions is not None:
            for dim_name in self._window_functions.keys():
                dim_index = self._dim_names.index(dim_name)

                window_size = self.window_functions[dim_name][1]
                half_window_size = int((window_size - 1) / 2)

                max_bound = self._data.shape[dim_index]

                window_indices = range()

        else:
            array = array[key]

        return array

    def __getitem__(self, key):
        data = self._data


        data = self._apply_window_functions(data, key)

        if self.frame_apply is not None:
            data = self.frame_apply(data)

        if data.ndim != self._display_dims:
            raise ValueError

        return data
