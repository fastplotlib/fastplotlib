from abc import ABC, abstractmethod
import numpy as np
import pygfx
from typing import *


class Graphic(ABC):
    def __init__(self, data, *args, **kwargs):
        self.data = data

    def update_data(self, data: Any):
        pass


class Image(Graphic):
    def __init__(self, data: np.ndarray, vmin: int, vmax: int, cmap: str = 'plasma', *args, **kwargs):
        super().__init__(data, *args, **kwargs)

        self.world_object = pygfx.Image(
            pygfx.Geometry(grid=pygfx.Texture(data, dim=2)),
            pygfx.ImageBasicMaterial(clim=(vmin, vmax), map=getattr(pygfx.cm, cmap))
        )

    def update_data(self, data: np.ndarray):
        self.world_object.geometry.data[:] = data
        self.world_object.geometry.update_range((0, 0, 0), self.world_object.geometry.grid.size)
