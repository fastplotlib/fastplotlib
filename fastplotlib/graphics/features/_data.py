from typing import *

import numpy as np
from pygfx import Buffer, Texture

from ._base import GraphicFeatureIndexable, cleanup_slice, FeatureEvent, to_gpu_supported_dtype, cleanup_array_slice


class PointsDataFeature(GraphicFeatureIndexable):
    """
    Access to the vertex buffer data shown in the graphic.
    Supports fancy indexing if the data array also supports it.
    """
    def __init__(self, parent, data: Any, collection_index: int = None):
        data = self._fix_data(data, parent)
        super(PointsDataFeature, self).__init__(parent, data, collection_index=collection_index)

    @property
    def buffer(self) -> Buffer:
        return self._parent.world_object.geometry.positions

    def __getitem__(self, item):
        return self.buffer.data[item]

    def _fix_data(self, data, parent):
        graphic_type = parent.__class__.__name__

        data = to_gpu_supported_dtype(data)

        if data.ndim == 1:
            # for scatter if we receive just 3 points in a 1d array, treat it as just a single datapoint
            # this is different from fix_data for LineGraphic since there we assume that a 1d array
            # is just y-values
            if graphic_type == "ScatterGraphic":
                data = np.array([data])
            elif graphic_type == "LineGraphic":
                data = np.dstack([np.arange(data.size, dtype=data.dtype), data])[0]

        if data.shape[1] != 3:
            if data.shape[1] != 2:
                raise ValueError(f"Must pass 1D, 2D or 3D data to {graphic_type}")

            # zeros for z
            zs = np.zeros(data.shape[0], dtype=data.dtype)

            data = np.dstack([data[:, 0], data[:, 1], zs])[0]

        return data

    def __setitem__(self, key, value):
        if isinstance(key, np.ndarray):
            # make sure 1D array of int or boolean
            key = cleanup_array_slice(key, self._upper_bound)

        # put data into right shape if they're only indexing datapoints
        if isinstance(key, (slice, int, np.ndarray, np.integer)):
            value = self._fix_data(value, self._parent)
        # otherwise assume that they have the right shape
        # numpy will throw errors if it can't broadcast

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
            "new_data": new_data
        }

        event_data = FeatureEvent(type="data", pick_info=pick_info)

        self._call_event_handlers(event_data)


class ImageDataFeature(GraphicFeatureIndexable):
    """
    Access to the Texture buffer shown in an ImageGraphic.
    """

    def __init__(self, parent, data: Any):
        if data.ndim not in (2, 3):
            raise ValueError(
                "`data.ndim` must be 2 or 3, ImageGraphic data shape must be "
                "``[x_dim, y_dim]`` or ``[x_dim, y_dim, rgb]``"
            )

        super(ImageDataFeature, self).__init__(parent, data)

    @property
    def buffer(self) -> Texture:
        """Texture buffer for the image data"""
        return self._parent.world_object.geometry.grid

    def update_gpu(self):
        """Update the GPU with the buffer"""
        self._update_range(None)

    def __call__(self, *args, **kwargs):
        return self.buffer.data

    def __getitem__(self, item):
        return self.buffer.data[item]

    def __setitem__(self, key, value):
        # make sure float32
        value = to_gpu_supported_dtype(value)

        self.buffer.data[key] = value
        self._update_range(key)

        # avoid creating dicts constantly if there are no events to handle
        if len(self._event_handlers) > 0:
            self._feature_changed(key, value)

    def _update_range(self, key):
        self.buffer.update_range((0, 0, 0), size=self.buffer.size)

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


class HeatmapDataFeature(ImageDataFeature):
    @property
    def buffer(self) -> List[Texture]:
        """list of Texture buffer for the image data"""
        return [img.geometry.grid for img in self._parent.world_object.children]

    def __getitem__(self, item):
        return self._data[item]

    def __call__(self, *args, **kwargs):
        return self._data

    def __setitem__(self, key, value):
        # make sure supported type, not float64 etc.
        value = to_gpu_supported_dtype(value)

        self._data[key] = value
        self._update_range(key)

        # avoid creating dicts constantly if there are no events to handle
        if len(self._event_handlers) > 0:
            self._feature_changed(key, value)

    def _update_range(self, key):
        for buffer in self.buffer:
            buffer.update_range((0, 0, 0), size=buffer.size)

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
