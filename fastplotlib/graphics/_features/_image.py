from math import ceil

import numpy as np
from numpy.typing import NDArray

import pygfx
from ._base import GraphicFeature, FeatureEvent, WGPU_MAX_TEXTURE_SIZE

from ...utils import (
    make_colors,
    get_cmap_texture,
)

# manages an array of 8192x8192 Textures representing chunks of an image
class TextureArray(GraphicFeature):

    def __init__(self, data, isolated_buffer: bool = True):
        super().__init__()

        data = self._fix_data(data)

        if isolated_buffer:
            # useful if data is read-only, example: memmaps
            self._value = np.zeros(data.shape, dtype=data.dtype)
            self.value[:] = data[:]
        else:
            # user's input array is used as the buffer
            self._value = data

        # indices for each Texture
        self._row_indices = np.arange(0, ceil(self.value.shape[0] / WGPU_MAX_TEXTURE_SIZE) * WGPU_MAX_TEXTURE_SIZE, WGPU_MAX_TEXTURE_SIZE)
        self._col_indices = np.arange(0, ceil(self.value.shape[1] / WGPU_MAX_TEXTURE_SIZE) * WGPU_MAX_TEXTURE_SIZE, WGPU_MAX_TEXTURE_SIZE)

        # buffer will be an array of textures
        self._buffer: np.ndarray[pygfx.Texture] = np.empty(shape=(self.row_indices.size, self.col_indices.size), dtype=object)

        # max index
        row_max = self.value.shape[0] - 1
        col_max = self.value.shape[1] - 1

        for (buffer_row, row_ix), (buffer_col, col_ix) in zip(enumerate(self.row_indices), enumerate(self.col_indices)):
            # stop index for this chunk
            row_stop = min(row_max, row_ix + WGPU_MAX_TEXTURE_SIZE)
            col_stop = min(col_max, col_ix + WGPU_MAX_TEXTURE_SIZE)

            # make texture from slice
            texture = pygfx.Texture(
                self.value[row_ix:row_stop, col_ix:col_stop], dim=2
            )

            self.buffer[buffer_row, buffer_col] = texture

        self._shared: int = 0

    @property
    def value(self) -> NDArray:
        return self._value

    def set_value(self, graphic, value):
        self[:] = value

    @property
    def buffer(self) -> np.ndarray[pygfx.Texture]:
        return self._buffer

    @property
    def row_indices(self) -> np.ndarray:
        return self._row_indices

    @property
    def col_indices(self) -> np.ndarray:
        return self._row_indices

    @property
    def shared(self) -> int:
        return self._shared

    def _fix_data(self, data):
        if data.ndim not in (2, 3):
            raise ValueError(
                "image data must be 2D with or without an RGB(A) dimension, i.e. "
                "it must be of shape [x, y], [x, y, 3] or [x, y, 4]"
            )

        # let's just cast to float32 always
        return data.astype(np.float32)

    def __getitem__(self, item):
        return self.value[item]

    def __setitem__(self, key, value):
        self.value[key] = value

        for texture in self.buffer.ravel():
            texture.update_range((0, 0, 0), texture.size)

        event = FeatureEvent("data", info={"key": key, "value": value})
        self._call_event_handlers(event)


class ImageVmin(GraphicFeature):
    """lower contrast limit"""
    def __init__(self, value: float):
        self._value = value
        super().__init__()

    @property
    def value(self) -> float:
        return self._value

    def set_value(self, graphic, value: float):
        vmax = graphic._material.clim[1]
        graphic._material.clim = (value, vmax)
        self._value = value

        event = FeatureEvent(type="vmin", info={"value": value})
        self._call_event_handlers(event)


class ImageVmax(GraphicFeature):
    """upper contrast limit"""
    def __init__(self, value: float):
        self._value = value
        super().__init__()

    @property
    def value(self) -> float:
        return self._value

    def set_value(self, graphic, value: float):
        vmin = graphic._material.clim[0]
        graphic._material.clim = (vmin, value)
        self._value = value

        event = FeatureEvent(type="vmax", info={"value": value})
        self._call_event_handlers(event)


class ImageCmap(GraphicFeature):
    """colormap for texture"""
    def __init__(self, value: str):
        self._value = value
        self.texture = get_cmap_texture(value)
        super().__init__()

    @property
    def value(self) -> str:
        return self._value

    def set_value(self, graphic, value: str):
        new_colors = make_colors(256, value)
        graphic._material.map.data[:] = new_colors
        graphic._material.map.update_range((0, 0, 0), size=(256, 1, 1))

        self._value = value
        event = FeatureEvent(type="cmap", info={"value": value})
        self._call_event_handlers(event)


class ImageInterpolation(GraphicFeature):
    """Image interpolation method"""
    def __init__(self, value: str):
        self._validate(value)
        self._value = value
        super().__init__()

    def _validate(self, value):
        if value not in ["nearest", "linear"]:
            raise ValueError("`interpolation` must be one of 'nearest' or 'linear'")

    @property
    def value(self) -> str:
        return self._value

    def set_value(self, graphic, value: str):
        self._validate(value)

        graphic._material.interpolation = value

        self._value = value
        event = FeatureEvent(type="interpolation", info={"value": value})
        self._call_event_handlers(event)


class ImageCmapInterpolation(GraphicFeature):
    """Image cmap interpolation method"""

    def __init__(self, value: str):
        self._validate(value)
        self._value = value
        super().__init__()

    def _validate(self, value):
        if value not in ["nearest", "linear"]:
            raise ValueError("`cmap_interpolation` must be one of 'nearest' or 'linear'")

    @property
    def value(self) -> str:
        return self._value

    def set_value(self, graphic, value: str):
        self._validate(value)

        # common material for all image tiles
        graphic._material.map_interpolation = value

        self._value = value
        event = FeatureEvent(type="cmap_interpolation", info={"value": value})
        self._call_event_handlers(event)
