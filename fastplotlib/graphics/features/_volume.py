from itertools import product
from math import ceil

import numpy as np
import pygfx

from ._base import GraphicFeature, GraphicFeatureEvent, block_reentrance

VOLUME_RENDER_MODES = {
    "mip": pygfx.VolumeMipMaterial,
    "minip": pygfx.VolumeMinipMaterial,
    "iso": pygfx.VolumeIsoMaterial,
    "slice": pygfx.VolumeSliceMaterial,
}


class TextureArrayVolume(GraphicFeature):
    """
    Manages an array of Textures representing chunks of an image. Chunk size is the GPU's max texture limit.

    Creates and manages multiple pygfx.Texture objects.
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

        self._texture_size_limit = shared.device.limits["max-texture-dimension-3d"]

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
            ceil(self.value.shape[1] / self._texture_size_limit)
            * self._texture_size_limit,
            self._texture_size_limit,
        )
        self._col_indices = np.arange(
            0,
            ceil(self.value.shape[2] / self._texture_size_limit)
            * self._texture_size_limit,
            self._texture_size_limit,
        )

        self._zdim_indices = np.arange(
            0,
            ceil(self.value.shape[0] / self._texture_size_limit)
            * self._texture_size_limit,
            self._texture_size_limit,
        )

        shape = (self.zdim_indices.size, self.row_indices.size, self.col_indices.size)

        # buffer will be an array of textures
        self._buffer: np.ndarray[pygfx.Texture] = np.empty(shape=shape, dtype=object)

        self._iter = None

        # iterate through each chunk of passed `data`
        # create a pygfx.Texture from this chunk
        for _, buffer_index, data_slice in self:
            texture = pygfx.Texture(self.value[data_slice], dim=3)

            self.buffer[buffer_index] = texture

        self._shared: int = 0

    @property
    def value(self) -> np.ndarray:
        """The full array that represents all the data within this TextureArray"""
        return self._value

    def set_value(self, graphic, value):
        self[:] = value

    @property
    def buffer(self) -> np.ndarray[pygfx.Texture]:
        """array of buffers that are mapped to the GPU"""
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
    def zdim_indices(self) -> np.ndarray:
        """
        z dimension indices that are used to chunk the big data array
        into individual Textures on the GPU
        """
        return self._zdim_indices

    @property
    def shared(self) -> int:
        return self._shared

    def _fix_data(self, data):
        if data.ndim not in (3, 4):
            raise ValueError(
                "Volume Image data must be 3D with or without an RGB(A) dimension, i.e. "
                "it must be of shape [z, rows, cols], [z, rows, cols, 3] or [z, rows, cols, 4]"
            )

        # let's just cast to float32 always
        return data.astype(np.float32)

    def __iter__(self):
        self._iter = product(
            enumerate(self.zdim_indices),
            enumerate(self.row_indices),
            enumerate(self.col_indices),
        )

        return self

    def __next__(
        self,
    ) -> tuple[pygfx.Texture, tuple[int, int, int], tuple[slice, slice, slice]]:
        """
        Iterate through each Texture within the texture array

        Returns
        -------
        Texture, tuple[int, int], tuple[slice, slice]
            | Texture: pygfx.Texture
            | tuple[int, int]: chunk index, i.e corresponding index of ``self.buffer`` array
            | tuple[slice, slice]: data slice of big array in this chunk and Texture
        """
        # chunk indices
        (
            (chunk_z, data_z_start),
            (chunk_row, data_row_start),
            (chunk_col, data_col_start),
        ) = next(self._iter)

        # indices for to self.buffer for this chunk
        chunk_index = (chunk_z, chunk_row, chunk_col)

        # stop indices of big data array for this chunk
        z_stop = min(self.value.shape[0], data_z_start + self._texture_size_limit)
        row_stop = min(self.value.shape[1], data_row_start + self._texture_size_limit)
        col_stop = min(self.value.shape[2], data_col_start + self._texture_size_limit)

        # zdim, row and column slices that slice the data for this chunk from the big data array
        data_slice = (
            slice(data_z_start, z_stop),
            slice(data_row_start, row_stop),
            slice(data_col_start, col_stop),
        )

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


def create_volume_material_kwargs(graphic, mode: str):
    kwargs = {
        "clim": (graphic.vmin, graphic.vmax),
        "map": graphic._texture_map,
        "interpolation": graphic.interpolation,
        "pick_write": True,
    }

    if mode == "iso":
        more_kwargs = {
            attr: getattr(graphic, attr)
            for attr in [
                "threshold",
                "step_size",
                "substep_size",
                "emissive",
                "shininess",
            ]
        }

    elif mode == "slice":
        more_kwargs = {"plane": graphic.plane}
    else:
        more_kwargs = {}

    kwargs.update(more_kwargs)
    return kwargs


class VolumeRenderMode(GraphicFeature):
    """Volume rendering mode, controls world object material"""

    event_info_spec = [
        {
            "dict key": "value",
            "type": "str",
            "description": "volume rendering mode that has been set",
        },
    ]

    def __init__(self, value: str):
        self._validate(value)
        self._value = value
        super().__init__()

    @property
    def value(self) -> str:
        return self._value

    def _validate(self, value):
        if value not in VOLUME_RENDER_MODES.keys():
            raise ValueError(
                f"Given render mode: {value} is invalid. Valid render modes are: {VOLUME_RENDER_MODES.keys()}"
            )

    @block_reentrance
    def set_value(self, graphic, value: str):
        self._validate(value)

        VolumeMaterialCls = VOLUME_RENDER_MODES[value]

        kwargs = create_volume_material_kwargs(graphic, mode=value)

        new_material = VolumeMaterialCls(**kwargs)
        # since the world object is a group
        for volume_tile in graphic.world_object.children:
            volume_tile.material = new_material

        # so we have one place to reference it
        graphic._material = new_material
        self._value = value

        event = GraphicFeatureEvent(type="mode", info={"value": value})
        self._call_event_handlers(event)


class VolumeIsoThreshold(GraphicFeature):
    """Isosurface threshold"""

    event_info_spec = [
        {
            "dict key": "value",
            "type": "float",
            "description": "new isosurface threshold",
        },
    ]

    def __init__(self, value: float):
        self._value = value
        super().__init__()

    @property
    def value(self) -> float:
        return self._value

    @block_reentrance
    def set_value(self, graphic, value: float):
        graphic._material.threshold = value
        self._value = graphic._material.threshold

        event = GraphicFeatureEvent(type="threshold", info={"value": value})
        self._call_event_handlers(event)


class VolumeIsoStepSize(GraphicFeature):
    """Isosurface step_size"""

    event_info_spec = [
        {
            "dict key": "value",
            "type": "float",
            "description": "new isosurface step_size",
        },
    ]

    def __init__(self, value: float):
        self._value = value
        super().__init__()

    @property
    def value(self) -> float:
        return self._value

    @block_reentrance
    def set_value(self, graphic, value: float):
        graphic._material.step_size = value
        self._value = graphic._material.step_size

        event = GraphicFeatureEvent(type="step_size", info={"value": value})
        self._call_event_handlers(event)


class VolumeIsoSubStepSize(GraphicFeature):
    """Isosurface substep_size"""

    event_info_spec = [
        {
            "dict key": "value",
            "type": "float",
            "description": "new isosurface step_size",
        },
    ]

    def __init__(self, value: float):
        self._value = value
        super().__init__()

    @property
    def value(self) -> float:
        return self._value

    @block_reentrance
    def set_value(self, graphic, value: float):
        graphic._material.substep_size = value
        self._value = graphic._material.substep_size

        event = GraphicFeatureEvent(type="step_size", info={"value": value})
        self._call_event_handlers(event)


class VolumeIsoEmissive(GraphicFeature):
    """Isosurface emissive color"""

    event_info_spec = [
        {
            "dict key": "value",
            "type": "pygfx.Color",
            "description": "new isosurface emissive color",
        },
    ]

    def __init__(self, value: pygfx.Color | str | tuple | np.ndarray):
        self._value = pygfx.Color(value)
        super().__init__()

    @property
    def value(self) -> pygfx.Color:
        return self._value

    @block_reentrance
    def set_value(self, graphic, value: pygfx.Color | str | tuple | np.ndarray):
        graphic._material.emissive = value
        self._value = graphic._material.emissive

        event = GraphicFeatureEvent(type="emissive", info={"value": value})
        self._call_event_handlers(event)


class VolumeIsoShininess(GraphicFeature):
    """Isosurface shininess"""

    event_info_spec = [
        {
            "dict key": "value",
            "type": "int",
            "description": "new isosurface shininess",
        },
    ]

    def __init__(self, value: int):
        self._value = value
        super().__init__()

    @property
    def value(self) -> int:
        return self._value

    @block_reentrance
    def set_value(self, graphic, value: float):
        graphic._material.shininess = value
        self._value = graphic._material.shininess

        event = GraphicFeatureEvent(type="shininess", info={"value": value})
        self._call_event_handlers(event)


class VolumeSlicePlane(GraphicFeature):
    """Volume plane"""

    event_info_spec = [
        {
            "dict key": "value",
            "type": "tuple[float, float, float, float]",
            "description": "new plane slice",
        },
    ]

    def __init__(self, value: tuple[float, float, float, float]):
        self._value = value
        super().__init__()

    @property
    def value(self) -> tuple[float, float, float, float]:
        return self._value

    @block_reentrance
    def set_value(self, graphic, value: tuple[float, float, float, float]):
        graphic._material.plane = value
        self._value = graphic._material.plane

        event = GraphicFeatureEvent(type="plane", info={"value": value})
        self._call_event_handlers(event)
