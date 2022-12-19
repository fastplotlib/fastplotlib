from typing import *
import numpy as np
import pygfx

from ._base import Graphic


class LineGraphic(Graphic):
    def __init__(
            self,
            data: Any,
            z_position: float = 0.0,
            size: float = 2.0,
            colors: Union[str, np.ndarray, Iterable] = "w",
            cmap: str = None,
            *args,
            **kwargs
    ):
        """
        Create a line Graphic, 2d or 3d

        Parameters
        ----------
        data: array-like
            Line data to plot, 2D must be of shape [n_points, 2], 3D must be of shape [n_points, 3]

        z_position: float, optional
            z-axis position for placing the graphic

        size: float, optional
            thickness of the line

        colors: str, array, or iterable
            specify colors as a single human readable string, a single RGBA array,
            or an iterable of strings or RGBA arrays

        cmap: str, optional
            apply a colormap to the line instead of assigning colors manually

        args
            passed to Graphic
        kwargs
            passed to Graphic
        """
        super(LineGraphic, self).__init__(data, colors=colors, cmap=cmap, *args, **kwargs)

        self.fix_data()

        if size < 1.1:
            material = pygfx.LineThinMaterial
        else:
            material = pygfx.LineMaterial

        self.data = np.ascontiguousarray(self.data)

        self._world_object: pygfx.Line = pygfx.Line(
            geometry=pygfx.Geometry(positions=self.data, colors=self.colors.data),
            material=material(thickness=size, vertex_colors=True)
        )

        self.world_object.position.z = z_position

    def fix_data(self):
        # TODO: data should probably be a property of any Graphic?? Or use set_data() and get_data()
        if self.data.ndim == 1:
            self.data = np.dstack([np.arange(self.data.size), self.data])[0].astype(np.float32)

        if self.data.shape[1] != 3:
            if self.data.shape[1] != 2:
                raise ValueError("Must pass 1D, 2D or 3D data")

            # zeros for z
            zs = np.zeros(self.data.shape[0], dtype=np.float32)

            self.data = np.dstack([self.data[:, 0], self.data[:, 1], zs])[0].astype(np.float32)

    def update_data(self, data: np.ndarray):
        self.data = data.astype(np.float32)
        self.fix_data()

        self.world_object.geometry.positions.data[:] = self.data
        self.world_object.geometry.positions.update_range()
