from typing import List

import numpy as np
import pygfx

from ._base import Graphic


class ScatterGraphic(Graphic):
    def __init__(self, data: np.ndarray, z_position: float = 0.0, size: int = 1, colors: np.ndarray = "w", cmap: str = None, *args, **kwargs):
        super(ScatterGraphic, self).__init__(data, colors=colors, cmap=cmap, *args, **kwargs)

        self.fix_data()

        sizes = np.full(self.data.shape[0], size, dtype=np.float32)

        self._world_object: pygfx.Points = pygfx.Points(
            pygfx.Geometry(positions=self.data, sizes=sizes, colors=self.colors.data),
            material=pygfx.PointsMaterial(vertex_colors=True, vertex_sizes=True)
        )

        self.world_object.position.z = z_position

    def fix_data(self):
        # TODO: data should probably be a property of any Graphic?? Or use set_data() and get_data()
        if self.data.ndim == 1:
            self.data = np.array([self.data])

        if self.data.shape[1] != 3:
            if self.data.shape[1] != 2:
                raise ValueError("Must pass 1D, 2D or 3D data")

            # zeros for z
            zs = np.zeros(self.data.shape[0], dtype=np.float32)

            self.data = np.dstack([self.data[:, 0], self.data[:, 1], zs])[0].astype(np.float32)

    def update_data(self, data: np.ndarray):
        self.data = data
        self.fix_data()

        self.world_object.geometry.positions.data[:] = self.data
        self.world_object.geometry.positions.update_range(self.data.shape[0])
