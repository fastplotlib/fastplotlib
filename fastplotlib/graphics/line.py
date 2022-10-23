import numpy as np
import pygfx

from fastplotlib.graphics._base import Graphic


class Line(Graphic):
    def __init__(self, data: np.ndarray, zlevel: float = None, size: float = 2.0, colors: np.ndarray = None, cmap: str = None, *args, **kwargs):
        super(Line, self).__init__(data, colors=colors, cmap=cmap, *args, **kwargs)

        if self.data.shape[1] != 3:
            if self.data.shape[1] != 2:
                raise ValueError("Must pass 2D or 3D data")
            # make it 2D with zlevel
            if zlevel == None:
                zlevel = 0

            # zeros
            zs = np.full(self.data.shape[0], fill_value=zlevel, dtype=np.float32)

            self.data = np.dstack([self.data[:, 0], self.data[:, 1], zs])[0]

        if size < 1.1:
            material = pygfx.LineThinMaterial
        else:
            material = pygfx.LineMaterial

        self.data = np.ascontiguousarray(self.data)

        self.world_object: pygfx.Line = pygfx.Line(
            geometry=pygfx.Geometry(positions=self.data, colors=self.colors),
            material=material(thickness=size, vertex_colors=True)
        )

    def update_data(self, data: np.ndarray):
        self.data = data.astype(np.float32)
        self.world_object.geometry.positions.data[:] = self.data
        self.world_object.geometry.positions.update_range()

    def update_colors(self, colors: np.ndarray):
        super(Line, self)._set_colors(colors=colors, colors_length=self.data.shape[0], cmap=None, alpha=None)

        self.world_object.geometry.colors.data[:] = self.colors
        self.world_object.geometry.colors.update_range()
