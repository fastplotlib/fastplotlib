from typing import Tuple, Any, List

import numpy as np
import pygfx

from ._base import Graphic, Interaction
from ..utils import quick_min_max, get_cmap_texture


class ImageGraphic(Graphic, Interaction):
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
    def indices(self) -> Any:
        pass

    @property
    def features(self) -> List[str]:
        pass

    def _set_feature(self, feature: str, new_data: Any, indices: Any):
        pass

    def _reset_feature(self):
        pass

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
        self.world_object.geometry.grid.update_range((0, 0, 0), self.world_object.geometry.grid.size)

