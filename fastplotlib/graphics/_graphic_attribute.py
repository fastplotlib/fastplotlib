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

        self._bounds = data.shape[0]

    def __setitem__(self, key, value):
        if abs(key.start) > self._bounds or abs(key.stop) > self._bounds:
            raise IndexError

        if isinstance(key, slice):
            start = key.start
            stop = key.stop
            step = key.step
            if step is None:
                step = 1

            indices = range(start, stop, step)

        elif isinstance(key, int):
            indices = [key]

        else:
            raise TypeError("Graphic features only support integer and numerical fancy indexing")

        new_data_size = len(indices)

        if not isinstance(value, np.ndarray):
            new_colors = np.repeat(np.array([Color(value)]), new_data_size, axis=0)

        elif isinstance(value, np.ndarray):
            if value.shape == (4,):
                new_colors = value.astype(np.float32)
                if new_data_size > 1:
                    new_colors = np.repeat(np.array([new_colors]), new_data_size, axis=0)

            elif value.shape[1] == 4 and value.ndim == 2:
                if not value.shape[0] == new_data_size:
                    raise ValueError("numpy array passed to color must be of shape (4,) or (n_colors_modify, 4)")
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