from abc import ABC, abstractmethod
from typing import *
from pygfx import Color
import numpy as np


class GraphicFeature(ABC):
    def __init__(self, parent, data: Any):
        self._parent = parent
        self._data = data

    @abstractmethod
    def __getitem__(self, item):
        pass

    @abstractmethod
    def __setitem__(self, key, value):
        pass

    @abstractmethod
    def _update_range(self, key):
        pass


class ColorFeature(GraphicFeature):
    def __init__(self, parent, data):
        data = parent.geometry.colors.data
        super(ColorFeature, self).__init__(parent, data)

        self._upper_bound = data.shape[0]

    def __setitem__(self, key, value):
        # parse numerical slice indices
        if isinstance(key, slice):
            start = key.start
            stop = key.stop
            step = key.step
            for attr in [start, stop, step]:
                if attr is None:
                    continue
                if attr < 0:
                    raise IndexError("Negative indexing not supported.")

            if start is None:
                start = 0

            if stop is None:
                stop = self._upper_bound

            elif stop > self._upper_bound:
                raise IndexError("Index out of bounds")

            step = key.step
            if step is None:
                step = 1

            key = slice(start, stop, step)
            indices = range(key.start, key.stop, key.step)

        # or single numerical index
        elif isinstance(key, int):
            if key > self._upper_bound:
                raise IndexError("Index out of bounds")
            indices = [key]

        else:
            raise TypeError("Graphic features only support integer and numerical fancy indexing")

        new_data_size = len(indices)

        if not isinstance(value, np.ndarray):
            color = np.array(Color(value))  # pygfx color parser
            # make it of shape [n_colors_modify, 4]
            new_colors = np.repeat(
                np.array([color]).astype(np.float32),
                new_data_size,
                axis=0
            )

        # if already a numpy array
        elif isinstance(value, np.ndarray):
            # if a single color provided as numpy array
            if value.shape == (4,):
                new_colors = value.astype(np.float32)
                # if there are more than 1 datapoint color to modify
                if new_data_size > 1:
                    new_colors = np.repeat(
                        np.array([new_colors]).astype(np.float32),
                        new_data_size,
                        axis=0
                    )

            elif value.shape[1] == 4 and value.ndim == 2:
                if value.shape[0] != new_data_size:
                    raise ValueError("numpy array passed to color must be of shape (4,) or (n_colors_modify, 4)")
                # if there is a single datapoint to change color of but user has provided shape [1, 4]
                if new_data_size == 1:
                    new_colors = value.ravel().astype(np.float32)
                else:
                    new_colors = value.astype(np.float32)

            else:
                raise ValueError("numpy array passed to color must be of shape (4,) or (n_colors_modify, 4)")

        self._parent.geometry.colors.data[key] = new_colors

        self._update_range(key)

    def _update_range(self, key):
        if isinstance(key, int):
            self._parent.geometry.colors.update_range(key, size=1)
        if key.step is None:
            # update range according to size using the offset
            self._parent.geometry.colors.update_range(offset=key.start, size=key.stop - key.start)

        else:
            step = key.step
            ixs = range(key.start, key.stop, step)
            # convert slice to indices
            for ix in ixs:
                self._parent.geometry.colors.update_range(ix, size=1)

    def __getitem__(self, item):
        return self._parent.geometry.colors.data[item]