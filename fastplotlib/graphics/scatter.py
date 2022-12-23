from typing import *

import numpy as np
import pygfx

from ._base import Graphic


class ScatterGraphic(Graphic):
    def __init__(self, data: np.ndarray, z_position: float = 0.0, sizes: Union[int, np.ndarray, list] = 1, colors: np.ndarray = "w", cmap: str = None, *args, **kwargs):
        super(ScatterGraphic, self).__init__(data, colors=colors, cmap=cmap, *args, **kwargs)

        if isinstance(sizes, int):
            sizes = np.full(self.data.feature_data.shape[0], sizes, dtype=np.float32)
        elif isinstance(sizes, np.ndarray):
            if (sizes.ndim != 1) or (sizes.size != self.data.feature_data.shape[0]):
                raise ValueError(f"numpy array of `sizes` must be 1 dimensional with "
                                 f"the same length as the number of datapoints")
        elif isinstance(sizes, list):
            if len(sizes) != self.data.feature_data.shape[0]:
                raise ValueError("list of `sizes` must have the same length as the number of datapoints")

        self._world_object: pygfx.Points = pygfx.Points(
            pygfx.Geometry(positions=self.data.feature_data, sizes=sizes, colors=self.colors.feature_data),
            material=pygfx.PointsMaterial(vertex_colors=True, vertex_sizes=True)
        )

        self.world_object.position.z = z_position
