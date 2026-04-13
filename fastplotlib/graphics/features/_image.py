from itertools import product
from math import ceil
from typing import Literal
from warnings import warn

import cmap as cmap_lib
import numpy as np

import wgpu
import pygfx

from ._base import GraphicFeature, GraphicFeatureEvent, block_reentrance

from ...utils import (
    get_cmap_texture,
)


class TextureArray(GraphicFeature):
    """
    Manages an array of Textures representing chunks of an image.

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

    def __init__(
        self,
        data,
        property_name: str = "data",
        cpu_buffer: bool = True,
        colorspace: Literal[
            "srgb", "tex-srgb", "physical", "yuv420p", "yuv444p"
        ] = "srgb",
        colorrange: Literal["full", "limited"] = "limited",
    ):
        super().__init__(property_name=property_name)

        if colorspace not in ("srgb", "tex-srgb", "physical", "yuv420p", "yuv444p"):
            raise ValueError(
                f"`colorspace` must be one of: 'srgb', 'tex-srgb', 'physical', 'yuv420p', 'yuv444p'\n"
                f"you passed: {colorspace}"
            )

        if colorrange not in ("full", "limited"):
            raise ValueError(
                f"`colorrange` must be one of 'full', 'limited'\n"
                f"you passed: {colorrange}"
            )

        if colorspace in ("yuv420p", "yuv444p"):
            # the only real use cases of yuv is video which is almost always going to be uint8
            format_ = "r8unorm"
        else:
            # let Texture auto-determine format
            format_ = None

        data = self._check_data(data, colorspace, cpu_buffer)

        shared = pygfx.renderers.wgpu.get_shared()
        self._texture_limit_2d = shared.device.limits["max-texture-dimension-2d"]

        if cpu_buffer:
            # create a local buffer
            self._value = np.zeros(data.shape, dtype=data.dtype)
            self.value[:] = data[:]
            usage = 0
        else:
            self._value = None
            usage = wgpu.TextureUsage.COPY_DST

        # data start indices for each Texture
        self._row_indices = np.arange(
            0,
            ceil(self.value.shape[0] / self._texture_limit_2d) * self._texture_limit_2d,
            self._texture_limit_2d,
        )
        self._col_indices = np.arange(
            0,
            ceil(self.value.shape[1] / self._texture_limit_2d) * self._texture_limit_2d,
            self._texture_limit_2d,
        )

        # buffer will be an array of textures
        self._buffer: np.ndarray[pygfx.Texture] = np.empty(
            shape=(self.row_indices.size, self.col_indices.size), dtype=object
        )

        if self._buffer.size > 1 and colorspace == "yuv420p":
            # for now don't support yuv420p with tiling textures, too complicated
            raise ValueError(
                f"colorspace yuv420p is currently not supported if the image dimensions exceed the device's "
                f"max-texture-dimension-2d. For now you must tile individual Images to use the yuv420p colorspace."
            )

        self._iter = None

        if colorspace in ("srgb", "tex-srgb", "physical"):
            depth = 1
        elif colorspace == "yuv420":
            depth = 2  # u and v get stored together in the 2nd layer
        elif colorspace == "yuv444p":
            depth = 3  # y, u, v get independent layers

        self._shape = data.shape

        # iterate through each chunk of passed `data`
        # create a pygfx.Texture from this chunk
        for _, buffer_index, slicer in self:
            chunk = self.value[slicer]

            if cpu_buffer:
                # texture gets the data directly
                texture = pygfx.Texture(
                    chunk,
                    dim=2,
                    colorspace=colorspace,
                    colorrange=colorrange,
                    format=format_,
                    usage=usage,
                )
            else:
                # we only supply the size
                w, h = chunk.shape[1], chunk.shape[0]
                texture = pygfx.Texture(
                    size=(w, h, depth),
                    dim=2,
                    colorspace=colorspace,
                    colorrange=colorrange,
                    format=format_,
                    usage=usage,
                )
                # send the initial data
                if colorspace == "yuv420p":
                    # assume yuv data is packed, reshape and send with respective offsets
                    y = chunk[:h]
                    u = chunk[h : h + h // 4].reshape(h // 2, w // 2)
                    v = chunk[h + h // 4 :].reshape(h // 2, w // 2)
                    texture.send_data((0, 0, 0), y)
                    texture.send_data((0, 0, 1), u)
                    texture.send_data((w // 2, 0, 1), v)
                else:
                    # all other colorspaces can be directly sent
                    texture.send_data((0, 0, 0), chunk)

            self.buffer[buffer_index] = texture

        self._colorspace = colorspace
        self._colorrange = colorrange
        self._cpu_buffer = cpu_buffer

    @property
    def colorspace(
        self,
    ) -> Literal["srgb", "tex-srgb", "physical", "yuv420p", "yuv444p"]:
        """Colorspace, read only"""
        return self._colorspace

    @property
    def colorrange(self) -> Literal["full", "limited"]:
        """Colorspace, read only property"""
        return self._colorrange

    @property
    def cpu_buffer(self) -> bool:
        """whether or not a cpu buffer exists for this TextureArray"""
        return self._cpu_buffer

    @property
    def shape(self) -> tuple[int, ...]:
        """
        the shape of the represented data
        if the colorspace is yuv420p then it is the shape of the _packed_ data
        """
        return self._shape

    @property
    def value(self) -> np.ndarray | None:
        """array buffer if Texture has a cpu buffer, otherwise None"""
        return self._value

    def set_value(self, graphic, value):
        if self.cpu_buffer:
            # if cpu_buffer is False, we directly send
            if value.shape != self.shape:
                raise ValueError(
                    f"new data shape must be the same as the original data array"
                    f"original data shape was: {self.shape}, data passed is of shape: {value.shape}"
                )
            # send everything
            if colorspace == "yuv420p":
                # yuv data is packed, reshape and send with respective offsets
                y = value[:h]
                u = value[h : h + h // 4].reshape(h // 2, w // 2)
                v = value[h + h // 4 :].reshape(h // 2, w // 2)
                texture.send_data((0, 0, 0), y)
                texture.send_data((0, 0, 1), u)
                texture.send_data((w // 2, 0, 1), v)
            else:
                # all other colorspaces can be directly sent
                texture.send_data((0, 0, 0), value)
        else:
            # set the cpu buffer, it will be marked for upload
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

    def _check_data(self, data, colorspace, cpu_buffer):
        # make sure data ndim is valid for the given colorspace

        if colorspace in ("srgb", "tex-srgb", "physical"):
            if data.ndim not in (2, 3):
                raise ValueError(
                    "if the colorspace is 'srgb', 'tex-srgb', or 'physical', "
                    "the image data must be 2D with or without an RGB(A) dimension, i.e. "
                    "it must be of shape [rows, cols], [rows, cols, 3] or [rows, cols, 4]"
                )

            if data.ndim == 3 and not cpu_buffer:
                # wgpu only supports rgba, it does not support rgb
                if data.shape[-1] != 4:
                    raise ValueError(
                        "if the colorspace is 'srgb', 'tex-srgb', or 'physical' and `cpu_buffer=False`"
                        "the image data MUST be RGBA, with shape [rows, cols, 4]. WGPU does not support "
                        "rgb textures. You must either supply full a RGBA array with `cpu_buffer=False` or "
                        "use `cpu_buffer=True` which supports RGB arrays."
                    )

        elif colorspace == "yuv420p":
            if data.ndim != 2:
                raise ValueError(
                    "if the colorspace is 'yuv420p' the data array must have 2 dimensions, "
                    "with the `u` and `v` values packed along the bottom rows of the 2D data array"
                )

        elif colorspace == "yuv444p":
            if data.ndim != 3 and data.shape[-1] != 3:
                raise ValueError(
                    "if the colorspace is 'yuv420p' the data array must have 3 dimensions, "
                    "the shape should be: [rows, cols, 3], i.e. a stack of 3 2D arrays that "
                    "represent y, u, v."
                )

        if data.itemsize == 8:
            warn(f"casting {data.dtype} array to float32")
            return data.astype(np.float32)

        return data

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
        row_stop = min(self.value.shape[0], data_row_start + self._texture_limit_2d)
        col_stop = min(self.value.shape[1], data_col_start + self._texture_limit_2d)

        # row and column slices that slice the data for this chunk from the big data array
        slicer = (slice(data_row_start, row_stop), slice(data_col_start, col_stop))

        # texture for this chunk
        texture = self.buffer[chunk_index]

        return texture, chunk_index, slicer

    def __getitem__(self, item):
        return self.value[item]

    @block_reentrance
    def __setitem__(self, key, value):
        if not self.cpu_buffer:
            raise BufferError(
                f"setting slices or specific elements of texture data is only supported when `cpu_buffer=True`."
                f"'unbuffered' textures only support setting the full data entirely, "
                f"i.e. you must do: graphic.data = new_arr, you cannot do: graphic.data[indices] = new_arr, unless "
                f"`cpu_buffer=True`"
            )

        self.value[key] = value

        for texture in self.buffer.ravel():
            texture.update_range((0, 0, 0), texture.size)

        event = GraphicFeatureEvent(
            self._property_name, info={"key": key, "value": value}
        )
        self._call_event_handlers(event)

    def __len__(self):
        return self.buffer.size


class ImageVmin(GraphicFeature):
    """lower contrast limit"""

    event_info_spec = [
        {
            "dict key": "value",
            "type": "float",
            "description": "new vmin value",
        },
    ]

    def __init__(self, value: float, property_name: str = "vmin"):
        self._value = value
        super().__init__(property_name=property_name)

    @property
    def value(self) -> float:
        return self._value

    @block_reentrance
    def set_value(self, graphic, value: float):
        vmax = graphic._material.clim[1]
        graphic._material.clim = (value, vmax)
        self._value = value

        event = GraphicFeatureEvent(type=self._property_name, info={"value": value})
        self._call_event_handlers(event)


class ImageVmax(GraphicFeature):
    """upper contrast limit"""

    event_info_spec = [
        {
            "dict key": "value",
            "type": "float",
            "description": "new vmax value",
        },
    ]

    def __init__(self, value: float, property_name: str = "vmax"):
        self._value = value
        super().__init__(property_name=property_name)

    @property
    def value(self) -> float:
        return self._value

    @block_reentrance
    def set_value(self, graphic, value: float):
        vmin = graphic._material.clim[0]
        graphic._material.clim = (vmin, value)
        self._value = value

        event = GraphicFeatureEvent(type=self._property_name, info={"value": value})
        self._call_event_handlers(event)


class ImageCmap(GraphicFeature):
    """colormap for texture"""

    event_info_spec = [
        {
            "dict key": "value",
            "type": "str",
            "description": "new cmap name",
        },
    ]

    def __init__(self, value: str, property_name: str = "cmap"):
        self._value = value
        self.texture = get_cmap_texture(value)
        super().__init__(property_name=property_name)

    @property
    def value(self) -> str:
        return self._value

    @block_reentrance
    def set_value(self, graphic, value: str):
        colormap = pygfx.cm.create_colormap(cmap_lib.Colormap(value).lut())
        graphic._material.map = colormap
        graphic._material.map.texture.update_range((0, 0, 0), size=(256, 1, 1))

        self._value = value
        event = GraphicFeatureEvent(type=self._property_name, info={"value": value})
        self._call_event_handlers(event)


class ImageInterpolation(GraphicFeature):
    """Image interpolation method"""

    event_info_spec = [
        {
            "dict key": "value",
            "type": "str",
            "description": "new interpolation method, nearest | linear",
        },
    ]

    def __init__(self, value: str, property_name: str = "interpolation"):
        self._validate(value)
        self._value = value
        super().__init__(property_name=property_name)

    def _validate(self, value):
        if value not in ["nearest", "linear"]:
            raise ValueError("`interpolation` must be one of 'nearest' or 'linear'")

    @property
    def value(self) -> str:
        return self._value

    @block_reentrance
    def set_value(self, graphic, value: str):
        self._validate(value)

        graphic._material.interpolation = value

        self._value = value
        event = GraphicFeatureEvent(type="interpolation", info={"value": value})
        self._call_event_handlers(event)


class ImageCmapInterpolation(GraphicFeature):
    """Image cmap interpolation method"""

    event_info_spec = [
        {
            "dict key": "value",
            "type": "str",
            "description": "new cmap interpolatio method, nearest | linear",
        },
    ]

    def __init__(self, value: str, property_name: str = "cmap_interpolation"):
        self._validate(value)
        self._value = value
        super().__init__(property_name=property_name)

    def _validate(self, value):
        if value not in ["nearest", "linear"]:
            raise ValueError(
                "`cmap_interpolation` must be one of 'nearest' or 'linear'"
            )

    @property
    def value(self) -> str:
        return self._value

    @block_reentrance
    def set_value(self, graphic, value: str):
        self._validate(value)

        # common material for all image tiles
        graphic._material.map.min_filter = value
        graphic._material.map.mag_filter = value

        self._value = value
        event = GraphicFeatureEvent(type=self._property_name, info={"value": value})
        self._call_event_handlers(event)
