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

        self.world_object: pygfx.Image = pygfx.Image(
            pygfx.Geometry(grid=pygfx.Texture(data, dim=2)),
            pygfx.ImageBasicMaterial(clim=(vmin, vmax), map=getattr(pygfx.cm, cmap))
        )

    @property
    def clim(self) -> Tuple[float, float]:
        return self.world_object.material.clim

    @clim.setter
    def clim(self, levels: Tuple[float, float]):
        self.world_object.material.clim = levels

    def update_data(self, data: np.ndarray):
        self.world_object.geometry.grid.data[:] = data
        self.world_object.geometry.grid.update_range((0, 0, 0), self.world_object.geometry.grid.size)
