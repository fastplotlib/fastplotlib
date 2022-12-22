from ._base import GraphicFeatureIndexable
from pygfx import Buffer
from typing import *
from ...utils import fix_data, to_float32


class DataFeature(GraphicFeatureIndexable):
    """
    Access to the buffer data being shown in the graphic.
    Supports fancy indexing if the data array also does.
    """
    # the correct data buffer is search for in this order
    data_buffer_names = ["grid", "positions"]

    def __init__(self, parent, data: Any, graphic_name):
        data = fix_data(data, graphic_name=graphic_name)
        self.graphic_name = graphic_name
        super(DataFeature, self).__init__(parent, data)

    @property
    def _buffer(self) -> Buffer:
        buffer = getattr(self._parent.world_object.geometry, self._buffer_name)
        return buffer

    @property
    def _buffer_name(self) -> str:
        for buffer_name in self.data_buffer_names:
            if hasattr(self._parent.world_object.geometry, buffer_name):
                return buffer_name

    def __getitem__(self, item):
        return self._buffer.data[item]

    def __setitem__(self, key, value):
        if isinstance(key, (slice, int)):
            # data must be provided in the right shape
            value = fix_data(value, graphic_name=self.graphic_name)
        else:
            # otherwise just make sure float32
            value = to_float32(value)
        self._buffer.data[key] = value
        self._update_range(key)

    def _update_range(self, key):
        if self._buffer_name == "grid":
            self._update_range_grid(key)
        elif self._buffer_name == "positions":
            self._update_range_indices(key)

    def _update_range_grid(self, key):
        # image data
        self._buffer.update_range((0, 0, 0), self._buffer.size)

    def __repr__(self):
        return repr(self._buffer.data)
