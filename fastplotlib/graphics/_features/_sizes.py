from typing import Any

import numpy as np

import pygfx

from ._base import (
    GraphicFeatureIndexable,
    cleanup_slice,
    FeatureEvent,
    to_gpu_supported_dtype,
    cleanup_array_slice,
)


class PointsSizesFeature(GraphicFeatureIndexable):
    """
    Access to the vertex buffer data shown in the graphic.
    Supports fancy indexing if the data array also supports it.
    """

    def __init__(self, parent, sizes: Any, collection_index: int = None):
        sizes = self._fix_sizes(sizes, parent)
        super(PointsSizesFeature, self).__init__(
            parent, sizes, collection_index=collection_index
        )

    @property
    def buffer(self) -> pygfx.Buffer:
        return self._parent.world_object.geometry.sizes

    def __getitem__(self, item):
        return self.buffer.data[item]

    def _fix_sizes(self, sizes, parent):
        graphic_type = parent.__class__.__name__
        
        n_datapoints = parent.data().shape[0]
        if not isinstance(sizes, (list, tuple, np.ndarray)):
            sizes = np.full(n_datapoints, sizes, dtype=np.float32) # force it into a float to avoid weird gpu errors
        elif not isinstance(sizes, np.ndarray): # if it's not a ndarray already, make it one
            sizes = np.array(sizes, dtype=np.float32) # read it in as a numpy.float32
            if (sizes.ndim != 1) or (sizes.size != parent.data().shape[0]):
                raise ValueError(
                    f"sequence of `sizes` must be 1 dimensional with "
                    f"the same length as the number of datapoints"
                )

        sizes = to_gpu_supported_dtype(sizes)

        if any(s < 0 for s in sizes):
            raise ValueError("All sizes must be positive numbers greater than or equal to 0.0.")

        if sizes.ndim == 1:
            if graphic_type == "ScatterGraphic":
                sizes = np.array(sizes)
        else:
            raise ValueError(f"Sizes must be an array of shape (n,) where n == the number of data points provided.\
                             Received shape={sizes.shape}.")

        return np.array(sizes)

    def __setitem__(self, key, value):
        if isinstance(key, np.ndarray):
            # make sure 1D array of int or boolean
            key = cleanup_array_slice(key, self._upper_bound)

        # put sizes into right shape if they're only indexing datapoints
        if isinstance(key, (slice, int, np.ndarray, np.integer)):
            value = self._fix_sizes(value, self._parent)
        # otherwise assume that they have the right shape
        # numpy will throw errors if it can't broadcast

        if value.size != self.buffer.data[key].size:
            raise ValueError(f"{value.size} is not equal to buffer size {self.buffer.data[key].size}.\
                             If you want to set size to a non-scalar value, make sure it's the right length!")

        self.buffer.data[key] = value
        self._update_range(key)
        # avoid creating dicts constantly if there are no events to handle
        if len(self._event_handlers) > 0:
            self._feature_changed(key, value)

    def _update_range(self, key):
        self._update_range_indices(key)

    def _feature_changed(self, key, new_data):
        if key is not None:
            key = cleanup_slice(key, self._upper_bound)
        if isinstance(key, (int, np.integer)):
            indices = [key]
        elif isinstance(key, slice):
            indices = range(key.start, key.stop, key.step)
        elif isinstance(key, np.ndarray):
            indices = key
        elif key is None:
            indices = None

        pick_info = {
            "index": indices,
            "collection-index": self._collection_index,
            "world_object": self._parent.world_object,
            "new_data": new_data,
        }

        event_data = FeatureEvent(type="sizes", pick_info=pick_info)

        self._call_event_handlers(event_data)

    def __repr__(self) -> str:
        s = f"PointsSizesFeature for {self._parent}, call `<graphic>.sizes()` to get values"
        return s
