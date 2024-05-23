import numpy as np

import pygfx
from ._base import GraphicFeature, BufferManager, FeatureEvent

from ...utils import (
    make_colors,
    get_cmap_texture,
)


class ImageData(BufferManager):
    def __init__(self, data, isolated_buffer: bool = True):
        data = self._fix_data(data)
        super().__init__(data, buffer_type="texture", isolated_buffer=isolated_buffer)

    @property
    def buffer(self) -> pygfx.Texture:
        return self._buffer

    def _fix_data(self, data):
        if data.ndim not in (2, 3):
            raise ValueError(
                "image data must be 2D with or without an RGB(A) dimension, i.e. "
                "it must be of shape [x, y], [x, y, 3] or [x, y, 4]"
            )

        # let's just cast to float32 always
        return data.astype(np.float32)

    def __setitem__(self, key: int | slice | np.ndarray[int | bool] | tuple[slice | np.ndarray[int | bool]], value):
        # offset and size should be (width, height, depth), i.e. (columns, rows, depth)
        # offset and size for depth should always be 0, 1 for 2D images
        if isinstance(key, tuple):
            # multiple dims sliced
            if any([k is Ellipsis for k in key]):
                # let's worry about ellipsis later
                raise TypeError("ellipses not supported for indexing buffers")
            if len(key) in (2, 3):
                dim_os = list()  # hold offset and size for each dim
                for dim, k in enumerate(key[:2]):  # we only need width and height
                    dim_os.append(self._parse_offset_size(k, self.value.shape[dim]))

                # offset and size for each dim into individual offset and size tuple
                # note that this is flipped since we need (width, height) from (rows, cols)
                offset = (*tuple(os[1] for os in dim_os), 0)
                size = (*tuple(os[1] for os in dim_os), 0)
            else:
                raise IndexError

        else:
            # only first dim (rows) indexed
            row_offset, row_size = self._parse_offset_size(key, self.value.shape[0])
            offset = (0, row_offset, 0)
            size = (self.value.shape[1], row_size, 1)

        self.buffer.update_range(offset, size)
        self._emit_event("data", key, value)


class ImageVmin(GraphicFeature):
    """lower contrast limit"""
    def __init__(self, value: float):
        self._value = value
        super().__init__()

    @property
    def value(self) -> float:
        return self._value

    def set_value(self, graphic, value: float):
        vmax = graphic.world_object.material.clim[1]
        graphic.world_object.material.clim = (value, vmax)
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
        vmin = graphic.world_object.material.clim[0]
        graphic.world_object.material.clim = (vmin, value)
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
        graphic.world_object.material.map.data[:] = new_colors
        graphic.world_object.material.map.data.update_range((0, 0, 0), size=(256, 1, 1))

        self._value = value
        event = FeatureEvent(type="cmap", info={"value": value})
        self._call_event_handlers(event)
