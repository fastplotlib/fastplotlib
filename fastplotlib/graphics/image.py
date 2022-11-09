from typing import Tuple

import numpy as np
import pygfx

from ._base import Graphic
from ..utils import quick_min_max, get_cmap_texture


class Image(Graphic):
    def __init__(
            self,
            data: np.ndarray,
            vmin: int = None,
            vmax: int = None,
            cmap: str = 'plasma',
            *args,
            **kwargs
    ):
        if data.ndim != 2:
            raise ValueError("`data.ndim !=2`, you must pass only a 2D array to `data`")

        super().__init__(data, cmap=cmap, *args, **kwargs)

        if (vmin is None) or (vmax is None):
            vmin, vmax = quick_min_max(data)

        self.world_object: pygfx.Image = pygfx.Image(
            pygfx.Geometry(grid=pygfx.Texture(self.data, dim=2)),
            pygfx.ImageBasicMaterial(clim=(vmin, vmax), map=get_cmap_texture(cmap))
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

    def update_cmap(self, cmap: str, alpha: float = 1.0):
        self.world_object.material.map = get_cmap_texture(name=cmap)

    def __repr__(self):
        print("Fastplotlib Graphic: Image\n")
        if self.name is not None:
            print("Graphic Name: " + self.name + "\n")
            print("Graphic Location: " + hex(id(self)) + "\n")
        else:
            print("Graphic Location: " + hex(id(self)) + "\n")
        print(self.data)
        return ""
