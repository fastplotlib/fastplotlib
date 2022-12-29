from typing import *

import numpy as np
from pygfx import Buffer, Texture

from ._base import GraphicFeatureIndexable, cleanup_slice, FeatureEvent


def to_float32(array):
    if isinstance(array, np.ndarray):
        return array.astype(np.float32, copy=False)

    return array


class PointsDataFeature(GraphicFeatureIndexable):
    """
    Access to the vertex buffer data shown in the graphic.
    Supports fancy indexing if the data array also supports it.
    """
    def __init__(self, parent, data: Any, collection_index: int = None):
        data = self._fix_data(data, parent)
        super(PointsDataFeature, self).__init__(parent, data, collection_index=collection_index)

    @property
    def _buffer(self) -> Buffer:
        return self._parent.world_object.geometry.positions

    def __getitem__(self, item):
        return self._buffer.data[item]

    def _fix_data(self, data, parent):
        graphic_type = parent.__class__.__name__

        if data.ndim == 1:
            # for scatter if we receive just 3 points in a 1d array, treat it as just a single datapoint
            # this is different from fix_data for LineGraphic since there we assume that a 1d array
            # is just y-values
            if graphic_type == "ScatterGraphic":
                data = np.array([data])
            elif graphic_type == "LineGraphic":
                data = np.dstack([np.arange(data.size), data])[0].astype(np.float32)

        if data.shape[1] != 3:
            if data.shape[1] != 2:
                raise ValueError(f"Must pass 1D, 2D or 3D data to {graphic_type}")

            # zeros for z
            zs = np.zeros(data.shape[0], dtype=np.float32)

            data = np.dstack([data[:, 0], data[:, 1], zs])[0]

        return data

    def __setitem__(self, key, value):
        # put data into right shape if they're only indexing datapoints
        if isinstance(key, (slice, int)):
            value = self._fix_data(value, self._parent)
        # otherwise assume that they have the right shape
        # numpy will throw errors if it can't broadcast

        self._buffer.data[key] = value
        self._update_range(key)
        # avoid creating dicts constantly if there are no events to handle
        if len(self._event_handlers) > 0:
            self._feature_changed(key, value)

    def _update_range(self, key):
        self._update_range_indices(key)

    def _feature_changed(self, key, new_data):
        if key is not None:
            key = cleanup_slice(key, self._upper_bound)
        if isinstance(key, int):
            indices = [key]
        elif isinstance(key, slice):
            indices = range(key.start, key.stop, key.step)
        elif key is None:
            indices = None

        pick_info = {
            "index": indices,
            "collection-index": self._collection_index,
            "world_object": self._parent.world_object,
            "new_data": new_data
        }

        event_data = FeatureEvent(type="data", pick_info=pick_info)

        self._call_event_handlers(event_data)


class ImageDataFeature(GraphicFeatureIndexable):
    """
    Access to the TextureView buffer shown in an ImageGraphic.
    """

    def __init__(self, parent, data: Any):
        if data.ndim != 2:
            raise ValueError("`data.ndim !=2`, you must pass only a 2D array to an Image graphic")

        data = to_float32(data)
        super(ImageDataFeature, self).__init__(parent, data)

    @property
    def _buffer(self) -> Texture:
        return self._parent.world_object.geometry.grid.texture

    def __getitem__(self, item):
        return self._buffer.data[item]

    def __setitem__(self, key, value):
        # make sure float32
        value = to_float32(value)

        self._buffer.data[key] = value
        self._update_range(key)

        # avoid creating dicts constantly if there are no events to handle
        if len(self._event_handlers) > 0:
            self._feature_changed(key, value)

    def _update_range(self, key):
        self._buffer.update_range((0, 0, 0), size=self._buffer.size)

    def _feature_changed(self, key, new_data):
        if key is not None:
            key = cleanup_slice(key, self._upper_bound)
        if isinstance(key, int):
            indices = [key]
        elif isinstance(key, slice):
            indices = range(key.start, key.stop, key.step)
        elif key is None:
            indices = None

        pick_info = {
            "index": indices,
            "world_object": self._parent.world_object,
            "new_data": new_data
        }

        event_data = FeatureEvent(type="data", pick_info=pick_info)

        self._call_event_handlers(event_data)
