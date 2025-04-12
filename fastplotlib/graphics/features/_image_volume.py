from itertools import product

from math import ceil

import numpy as np

import pygfx
from ._base import GraphicFeature, GraphicFeatureEvent, block_reentrance

from ...utils import (
    make_colors,
    get_cmap_texture,
)


class TextureArray3D(GraphicFeature):
    """
    Manages an array of 3D Textures representing chunks of an image volume.

    Creates multiple pygfx.Texture objects based on the GPU's max texture dimension limit.
    """
    event_info_spec = [
        {
            "dict key": "key",
            "type": "slice, index, numpy-like fancy index",
            "description": "key at which image data was sliced/fancy indexed",
        },
        {
            "dict key": "value",
            "type": "np.ndarray | float",
            "description": "new data values",
        },
    ]

    def __init__(self, data, isolated_buffer: bool = True):
        super().__init__()

        data = self._fix_data(data)

        shared = pygfx.renderers.wgpu.get_shared()
        self._texture_limit_3d = shared.device.limits["max-texture-dimension-3d"]

        if isolated_buffer:
            # useful if data is read-only, example: memmaps
            self._value = np.zeros(data.shape, dtype=data.dtype)
            self.value[:] = data[:]
        else:
            # user's input array is used as the buffer
            self._value = data

        # data start indices for each Texture
        self._row_indices = np.arange(
            0,
            ceil(self.value.shape[0] / self._texture_limit_3d) * self._texture_limit_3d,
            self._texture_limit_3d,
        )
        self._col_indices = np.arange(
            0,
            ceil(self.value.shape[1] / self._texture_limit_3d) * self._texture_limit_3d,
            self._texture_limit_3d,
        )

        self._col_indices = np.arange(
            0,
            ceil(self.value.shape[1] / self._texture_limit_3d) * self._texture_limit_3d,
            self._texture_limit_3d,
        )

        # buffer will be an array of textures
        self._buffer: np.ndarray[pygfx.Texture] = np.empty(
            shape=(self.row_indices.size, self.col_indices.size), dtype=object
        )

        self._iter = None

        # iterate through each chunk of passed `data`
        # create a pygfx.Texture from this chunk
        for _, buffer_index, data_slice in self:
            texture = pygfx.Texture(self.value[data_slice], dim=2)

            self.buffer[buffer_index] = texture

        self._shared: int = 0

    @property
    def value(self) -> np.ndarray:
        return self._value

    def set_value(self, graphic, value):
        self[:] = value

    @property
    def buffer(self) -> np.ndarray[pygfx.Texture]:
        return self._buffer

    @property
    def row_indices(self) -> np.ndarray:
        """
        row indices that are used to chunk the big data array
        into individual Textures on the GPU
        """
        return self._row_indices

    @property
    def col_indices(self) -> np.ndarray:
        """
        column indices that are used to chunk the big data array
        into individual Textures on the GPU
        """
        return self._col_indices

    @property
    def shared(self) -> int:
        return self._shared

    def _fix_data(self, data):
        if data.ndim not in (2, 3):
            raise ValueError(
                "image data must be 2D with or without an RGB(A) dimension, i.e. "
                "it must be of shape [rows, cols], [rows, cols, 3] or [rows, cols, 4]"
            )

        # let's just cast to float32 always
        return data.astype(np.float32)

    def __iter__(self):
        self._iter = product(enumerate(self.row_indices), enumerate(self.col_indices))
        return self

    def __next__(self) -> tuple[pygfx.Texture, tuple[int, int], tuple[slice, slice]]:
        """
        Iterate through each Texture within the texture array

        Returns
        -------
        Texture, tuple[int, int], tuple[slice, slice]
            | Texture: pygfx.Texture
            | tuple[int, int]: chunk index, i.e corresponding index of ``self.buffer`` array
            | tuple[slice, slice]: data slice of big array in this chunk and Texture
        """
        (chunk_row, data_row_start), (chunk_col, data_col_start) = next(self._iter)

        # indices for to self.buffer for this chunk
        chunk_index = (chunk_row, chunk_col)

        # stop indices of big data array for this chunk
        row_stop = min(self.value.shape[0], data_row_start + self._texture_limit_3d)
        col_stop = min(self.value.shape[1], data_col_start + self._texture_limit_3d)

        # row and column slices that slice the data for this chunk from the big data array
        data_slice = (slice(data_row_start, row_stop), slice(data_col_start, col_stop))

        # texture for this chunk
        texture = self.buffer[chunk_index]

        return texture, chunk_index, data_slice

    def __getitem__(self, item):
        return self.value[item]

    @block_reentrance
    def __setitem__(self, key, value):
        self.value[key] = value

        for texture in self.buffer.ravel():
            texture.update_range((0, 0, 0), texture.size)

        event = GraphicFeatureEvent("data", info={"key": key, "value": value})
        self._call_event_handlers(event)

    def __len__(self):
        return self.buffer.size