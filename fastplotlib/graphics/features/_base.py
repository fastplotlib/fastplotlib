from abc import ABC, abstractmethod
from typing import *

import numpy as np
from pygfx import Buffer


class GraphicFeature(ABC):
    def __init__(self, parent, data: Any):
        self._parent = parent
        if isinstance(data, np.ndarray):
            data = data.astype(np.float32)

        self._data = data

    @property
    def feature_data(self):
        """graphic feature data managed by fastplotlib, do not modify directly"""
        return self._data

    @abstractmethod
    def _set(self, value):
        pass

    @abstractmethod
    def __repr__(self):
        pass


def cleanup_slice(slice_obj: slice, upper_bound) -> slice:
    if isinstance(slice_obj, tuple):
        if isinstance(slice_obj[0], slice):
            slice_obj = slice_obj[0]
        else:
            raise TypeError("Tuple slicing must have slice object in first position")

    if not isinstance(slice_obj, slice):
        raise TypeError("Must pass slice object")

    start = slice_obj.start
    stop = slice_obj.stop
    step = slice_obj.step
    for attr in [start, stop, step]:
        if attr is None:
            continue
        if attr < 0:
            raise IndexError("Negative indexing not supported.")

    if start is None:
        start = 0

    if stop is None:
        stop = upper_bound

    elif stop > upper_bound:
        raise IndexError("Index out of bounds")

    step = slice_obj.step
    if step is None:
        step = 1

    return slice(start, stop, step)


class GraphicFeatureIndexable(GraphicFeature):
    """And indexable Graphic Feature, colors, data, sizes etc."""

    def _set(self, value):
        self[:] = value

    @abstractmethod
    def __getitem__(self, item):
        pass

    @abstractmethod
    def __setitem__(self, key, value):
        pass

    @abstractmethod
    def _update_range(self, key):
        pass

    @property
    @abstractmethod
    def _buffer(self) -> Buffer:
        pass

    @property
    def _upper_bound(self) -> int:
        return self.feature_data.shape[0]

    def _update_range_indices(self, key):
        """Currently used by colors and data"""
        if isinstance(key, int):
            self._buffer.update_range(key, size=1)
            return

        # else assume it's a slice or tuple of slice
        # if tuple of slice we only need the first obj
        # since the first obj is the datapoint indices
        key = cleanup_slice(key, self._upper_bound)

        # else if it's a single slice
        if isinstance(key, slice):
            if key.step == 1:  # we cleaned up the slice obj so step of None becomes 1
                # update range according to size using the offset
                self._buffer.update_range(offset=key.start, size=key.stop - key.start)

            else:
                step = key.step
                # convert slice to indices
                ixs = range(key.start, key.stop, step)
                for ix in ixs:
                    self._buffer.update_range(ix, size=1)
        else:
            raise TypeError("must pass int or slice to update range")


