from itertools import product
from math import ceil
from typing import Literal, TypeAlias
from warnings import warn

import cmap as cmap_lib
import numpy as np
from numpy.typing import NDArray

import wgpu
import pygfx

from ._base import GraphicFeature, GraphicFeatureEvent, block_reentrance

from .utils import get_element_format_from_numpy_array
from ...utils import get_cmap_texture, ColorspacesRGB, ColorspacesYUV, ColorRange

TupleYUV: TypeAlias = tuple[NDArray[np.uint8], NDArray[np.uint8], NDArray[np.uint8]]


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
        usage: wgpu.TextureUsage = 0,
        colorspace: ColorspacesRGB = ColorspacesRGB.srgb,
    ):
        super().__init__(property_name=property_name)

        self._colorspace = ColorspacesRGB(colorspace)
        self._cpu_buffer = cpu_buffer
        data = self._check_data(data, colorspace, cpu_buffer)

        self._shape = data.shape

        shared = pygfx.renderers.wgpu.get_shared()
        self._texture_limit_2d = shared.device.limits["max-texture-dimension-2d"]

        if cpu_buffer:
            # create a local buffer
            self._value = np.empty(data.shape, dtype=data.dtype)
            self.value[:] = data[:]
            usage = usage
        else:
            self._value = None
            usage = wgpu.TextureUsage.COPY_DST | usage
            # auto-determine format, adapted from pygfx.Texture
            element_format = get_element_format_from_numpy_array(data)
            if element_format is None:
                raise ValueError(
                    f"Unsupported dtype/format for texture data: {data.dtype}"
                )

            if data.ndim == 3:
                nchannels = data.shape[-1]
            else:
                nchannels = 1
            format_ = (f"{nchannels}x" + element_format).lstrip("1x")

            self._shape = data.shape

        # data start indices for each Texture
        self._row_indices = np.arange(
            0,
            ceil(self.shape[0] / self._texture_limit_2d) * self._texture_limit_2d,
            self._texture_limit_2d,
        )
        self._col_indices = np.arange(
            0,
            ceil(self.shape[1] / self._texture_limit_2d) * self._texture_limit_2d,
            self._texture_limit_2d,
        )

        # buffer will be an array of textures
        self._buffer: NDArray[pygfx.Texture] = np.empty(
            shape=(self.row_indices.size, self.col_indices.size), dtype=object
        )

        self._iter = None

        # iterate through each chunk of passed `data`
        # create a pygfx.Texture from this chunk
        for _, buffer_index, slicer in self:
            if cpu_buffer:
                # texture gets the data directly
                texture = pygfx.Texture(
                    self.value[slicer],
                    dim=2,
                    colorspace=colorspace,
                    usage=usage
                )
            else:
                # we only supply the size
                w, h = data[slicer].shape[1], data[slicer].shape[0]

                texture = pygfx.Texture(
                    size=(w, h, 1),
                    dim=2,
                    colorspace=colorspace,
                    format=format_,
                    usage=usage,
                )

                # send the initial data
                texture.send_data((0, 0, 0), data[slicer])

            self.buffer[buffer_index] = texture

    @property
    def colorspace(
        self,
    ) -> ColorspacesRGB:
        """Colorspace, read only"""
        return self._colorspace

    @property
    def cpu_buffer(self) -> bool:
        """whether or not a cpu buffer exists for this TextureArray"""
        return self._cpu_buffer

    @property
    def shape(self) -> tuple[int, int] | tuple[int, int, int]:
        """
        the shape of the represented data, [n_rows, n_cols] or [n_rows, n_cols, 3 | 4]
        """
        return self._shape

    @property
    def value(self) -> np.ndarray | None:
        """array buffer if Texture has a cpu buffer, otherwise None"""
        return self._value

    def set_value(self, graphic, value: np.ndarray):
        if not self.cpu_buffer:
            if isinstance(value, np.ndarray):
                # if cpu_buffer is False, we directly send data to the GPU
                if value.shape != self.shape:
                    raise ValueError(
                        f"new data shape must be the same as the original data array if `cpu_buffer=False`"
                        f"original data shape was: {self.shape}, data passed is of shape: {value.shape}"
                    )
                for texture, buffer_index, slicer in self:
                    chunk = value[slicer]
                    texture.send_data((0, 0, 0), chunk)

        else:
            # set the cpu buffer, it will be marked for upload
            self[:] = value

    @property
    def buffer(self) -> NDArray[pygfx.Texture]:
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

        if data.ndim not in (2, 3):
            raise ValueError(
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
        row_stop = min(self.shape[0], data_row_start + self._texture_limit_2d)
        col_stop = min(self.shape[1], data_col_start + self._texture_limit_2d)

        # row and column slices that slice the data for this chunk from the big data array
        slicer = (slice(data_row_start, row_stop), slice(data_col_start, col_stop))

        # texture for this chunk
        texture = self.buffer[chunk_index]

        return texture, chunk_index, slicer

    def __getitem__(self, item):
        if not self.cpu_buffer:
            return None

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


class TextureYUV(GraphicFeature):
    """
    Manages a YUV texture, no chunking, no local buffer
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
        data: TupleYUV,
        property_name: str = "data",
        colorspace: ColorspacesYUV = ColorspacesYUV.yuv420p,
        colorrrange: ColorRange = ColorRange.limited,
    ):
        super().__init__(property_name=property_name)

        self._colorspace = ColorspacesYUV(colorspace)
        self._colorrange = ColorRange(colorrrange)

        self._check_data(data)

        self._data = data

        shared = pygfx.renderers.wgpu.get_shared()
        limit = shared.device.limits["max-texture-dimension-2d"]
        if data[0].shape[0] > limit or data[0].shape[1] > limit:
            raise ValueError(
                f"YUV colorspaces Images currently don't support dimensions that exceed the device's "
                f"max-texture-dimension-2d. For now you must manually tile individual Images to use a YUV colorspace."
            )

        self._allocate_texture(data)
        self._send_data(data)

    @property
    def cpu_buffer(self) -> Literal[False]:
        return False

    @property
    def texture(self) -> pygfx.Texture:
        return self._texture

    @property
    def colorspace(self) -> ColorspacesYUV:
        return self._colorspace

    @property
    def colorrange(self) -> ColorRange:
        return self._colorrange

    def _allocate_texture(self, data: TupleYUV):
        """Create a new pygfx.Texture"""

        self._h, self._w = data[0].shape
        if self.colorspace == ColorspacesYUV.yuv420p:
            depth = 2
        else:
            depth = 3

        self._texture = pygfx.Texture(
            size=(self._w, self._h, depth),
            dim=2,
            colorspace=self.colorspace.value,
            colorrange=self.colorrange.value,
            format="r8unorm",
            usage=wgpu.TextureUsage.COPY_DST,
        )

    def _send_data(self, data):
        """send the data to the GPU"""
        y, u, v = data

        self._texture.send_data((0, 0, 0), y)

        if self.colorspace == ColorspacesYUV.yuv420p:
            self._texture.send_data((0, 0, 1), u)
            self._texture.send_data((self._w // 2, 0, 1), v)
        else:
            self._texture.send_data((0, 0, 1), u)
            self._texture.send_data((0, 0, 2), v)

    @property
    def value(self) -> None:
        """this is bufferless"""
        return None

    def set_value(self, graphic, value: TupleYUV):
        self._check_data(value)

        y, u, v = value

        if y.shape[0] != self._h or y.shape[1] != self._w:
            self._allocate_texture(value)
            graphic.geometry.grid = self._texture

        self._send_data(value)

    def _check_data(self, data: TupleYUV):
        err = f"must provide a tuple/list of np.ndarray of type np.uint8 representing YUV components."

        if not isinstance(data, (tuple, list)):
            raise TypeError(err + f"\nYou provided: {data}")

        if not len(data) == 3:
            raise TypeError(err + f"\nYou provided data of len: {len(data)}")

        if not all([isinstance(a, np.ndarray) for a in data]):
            raise TypeError(err + f"\nYou provided types: {[type(d) for d in data]}")

        types = [a.dtype for a in data]
        if not all([t == np.uint8 for t in types]):
            raise TypeError(err + f"\nYou provided data of types: {types}")

        if self.colorspace == ColorspacesYUV.yuv420p:
            err += (
                f"For {self.colorspace} UV channels must be 4x smaller than Y. "
                f"You provided shapes: {tuple(d.shape for d in data)}"
            )
            shapes = tuple(np.asarray(d.shape) for d in data)
            expected_uv_shape = shapes[0] // 2
            if (shapes[1] != expected_uv_shape).all() or (
                shapes[2] != expected_uv_shape
            ).all():
                raise ValueError(err)

        else:
            err += (
                f"For {self.colorspace} UV channels must be the same size as Y"
                f"You provided shapes: {tuple(d.shape for d in data)}"
            )

            if data[0].shape != data[1].shape or data[0].shape != data[2].shape:
                raise ValueError(err)


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


class ImageGamma(GraphicFeature):
    """gamma correction applied to the image"""

    event_info_spec = [
        {
            "dict key": "value",
            "type": "float",
            "description": "new gamma value",
        },
    ]

    def __init__(self, value: float, property_name: str = "gamma"):
        self._value = value
        super().__init__(property_name=property_name)

    @property
    def value(self) -> float:
        return self._value

    @block_reentrance
    def set_value(self, graphic, value: float):
        graphic._material.gamma = value
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
