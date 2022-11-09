from typing import List

import numpy as np
import pygfx

from ._base import Graphic


class Scatter(Graphic):
    def __init__(self, data: np.ndarray, zlevel: float = None, size: int = 1, colors: np.ndarray = None, cmap: str = None, *args, **kwargs):
        super(Scatter, self).__init__(data, colors=colors, cmap=cmap, *args, **kwargs)

        if self.data.ndim == 1:
            # assume single 3D point
            if not self.data.size == 3:
                raise ValueError("If passing single you must specify all coordinates, i.e. x, y and z.")
        elif self.data.shape[1] != 3:
            if self.data.shape[1] == 2:
                # make it 2D with zlevel
                if zlevel == None:
                    zlevel = 0

                # zeros
                zs = np.full(self.data.shape[0], fill_value=zlevel, dtype=np.float32)

                self.data = np.dstack([self.data[:, 0], self.data[:, 1], zs])[0]
            if self.data.shape[1] > 3 or self.data.shape[1] < 1:
                raise ValueError("Must pass 2D or 3D data or a single point")

        self.world_object: pygfx.Group = pygfx.Group()
        self.points_objects: List[pygfx.Points] = list()

        for color in np.unique(self.colors, axis=0):
            positions = self._process_positions(
                self.data[np.all(self.colors == color, axis=1)]
            )

            points = pygfx.Points(
                pygfx.Geometry(positions=positions),
                pygfx.PointsMaterial(size=size, color=color)
            )

            self.world_object.add(points)
            self.points_objects.append(points)

    def _process_positions(self, positions: np.ndarray):
        if positions.ndim == 1:
            positions = np.array([positions])

        return positions

    def update_data(self, data: np.ndarray):
        positions = self._process_positions(data).astype(np.float32)

        self.points_objects[0].geometry.positions.data[:] = positions
        self.points_objects[0].geometry.positions.update_range(positions.shape[0])

    def __repr__(self):
        print("Fastplotlib Graphic: Scatter\n")
        if self.name is not None:
            print("Graphic Name: " + self.name + "\n")
            print("Graphic Location: " + hex(id(self)) + "\n")
        else:
            print("Graphic Location: " + hex(id(self)) + "\n")
        print(self.data)
        return ""
