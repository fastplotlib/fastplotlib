import numpy as np
from numpy.typing import NDArray
from typing import Literal, Callable
from warnings import warn


class ImageWidgetArray:
    def __init__(
            self,
            data: NDArray,
            rgb: bool = False,
            window_function: Callable = None,
            window_size: dict[str, int] = None,
            frame_function: Callable = None,
            n_display_dims: Literal[2, 3] = 2,
            dim_names: tuple[str] = None,
    ):
        """

        Parameters
        ----------
        data: NDArray
            array-like data, must have 2 or more dimensions

        window_function: Callable, optional
            function to apply to a window of data around the current index.
            The callable must take an `axis` kwarg.

        window_size: dict[str, int]
            dict of window sizes for each dim, maps dim names -> window size.
            Example: {"t": 5, "z": 3}.

            If a dim is not provided the window size is 0 for that dim, i.e. no window is taken along that dimension

        frame_function
        n_display_dims
        dim_names
        """
        self._data = data

        self._window_size = window_function
        self._window_size = window_size

        self._frame_function = frame_function

        self._rgb = rgb

        # default dim names for mn, tmn, and tzmn, ignore rgb dim if present
        if dim_names is None:
            if data.ndim == (2 + int(self.rgb)):
                dim_names = ("m", "n")

            elif data.ndim == (3 + int(self.rgb)):
                dim_names = ("t", "m", "n")

            elif data.ndim == (4 + int(self.rgb)):
                dim_names = ("t", "z", "m", "n")

            else:
                # create a tuple of str numbers for each time, ex: ("0", "1", "2", "3", "4", "5", "6")
                dim_names = tuple(map(str, range(data.ndim)))

        self._dim_names = dim_names

        for k in self._window_size:
            if k not in dim_names:
                raise KeyError

        if n_display_dims not in (2, 3):
            raise ValueError("`n_display_dims` must be an <int> with a value of 2 or 3")

        self._n_display_dims = n_display_dims

    @property
    def data(self) -> NDArray:
        return self._data

    @data.setter
    def data(self, data: NDArray):
        self._data = data

    @property
    def rgb(self) -> bool:
        return self._rgb

    @property
    def ndim(self) -> int:
        return self.data.ndim

    @property
    def n_scrollable_dims(self) -> int:
        return self.ndim - 2 - int(self.rgb)

    @property
    def n_display_dims(self) -> int:
        return self._n_display_dims

    @property
    def dim_names(self) -> tuple[str]:
        return self._dim_names

    @property
    def window_function(self) -> Callable | None:
        return self._window_size

    @window_function.setter
    def window_function(self, func: Callable | None):
        self._window_size = func

    @property
    def window_size(self) -> dict | None:
        """dict of window sizes for each dim"""
        return self._window_size

    @window_size.setter
    def window_size(self, size: dict):
        for k in list(size.keys()):
            if k not in self.dim_names:
                raise ValueError(f"specified window key: `k` not present in array with dim names: {self.dim_names}")

            if not isinstance(size[k], int):
                raise TypeError("window size values must be integers")

            if size[k] < 0:
                raise ValueError(f"window size values must be greater than 2 and odd numbers")

            if size[k] == 0:
                # remove key
                warn(f"specified window size of 0 for dim: {k}, removing dim from windows")
                size.pop(k)

            elif size[k] % 2 != 0:
                # odd number, add 1
                warn(f"specified even number for window size of dim: {k}, adding one to make it even")
                size[k] += 1

        self._window_size = size

    @property
    def frame_function(self) -> Callable | None:
        return self._frame_function

    @frame_function.setter
    def frame_function(self, fa: Callable | None):
        self._frame_function = fa

    def _apply_window_function(self, index: dict[str, int]):
        if self.n_scrollable_dims == 0:
            # 2D image, return full data
            # TODO: would be smart to handle this in ImageWidget so
            #  that Texture buffer is not updated when it doesn't change!!
            return self.data

        if self.window_size is None:
            # for simplicity, so we can use the same for loop below to slice the array
            # regardless of whether window_functions are specified or not
            window_size = dict()
        else:
            window_size = self.window_size

        # create a slice object for every dim except the last 2, or 3 (if rgb)
        multi_slice = list()
        axes = list()

        for dim_number in range(self.n_scrollable_dims):
            # get str name
            dim_name = self.dim_names[dim_number]

            # don't go beyond max bound
            max_bound = self.data.shape[dim_number]

            # check if a window is specified for this dim
            if dim_name in window_size.keys():
                size = window_size[dim_name]
                half_size = int((size - 1) / 2)

                # create slice obj for this dim using this window
                start = max(0, index[dim_name] - half_size)  # start index, min allowed value is 0
                stop = min(max_bound, index[dim_name] + half_size)

                s = slice(start, stop)
                multi_slice.append(s)

                # add to axes list for window function
                axes.append(dim_number)
            else:
                # no window size is specified for this scrollable dim, directly use integer index
                multi_slice.append(index[dim_name])

            # get sliced array
            array_sliced = self.data[tuple(multi_slice)]

        if self.window_function is not None:
            # apply window function
            return self.window_function(array_sliced, axis=axes)

        # not window function, return sliced array
        return array_sliced

    def get(self, index: dict[str, int]):
        """
        Get the data at the given index, process data through the window function and frame function.

        Note that we do not use __getitem__ here since the index is a dict specifying a single integer
        index for each dimension. Slices are not allowed, therefore __getitem__ is not suitable here.

        Parameters
        ----------
        index: dict[str, int]
            Get the processed data at this index.
            Example: get({"t": 1000, "z" 3})

        """

        if set(index.keys()) != set(self.dim_names):
            raise ValueError(
                f"Must specify index for every dim, you have specified an index: {index}\n"
                f"All dim names are: {self.dim_names}"
            )

        window_output = self._apply_window_function(index)

        if self.frame_function is not None:
            frame_output = self.frame_function(window_output)
        else:
            frame_output = window_output

        if frame_output.ndim != self.n_display_dims:
            raise ValueError

        return frame_output
