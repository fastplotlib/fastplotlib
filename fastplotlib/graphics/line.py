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

        if size < 1.1:
            material = pygfx.LineThinMaterial
        else:
            material = pygfx.LineMaterial

        # self.data = np.ascontiguousarray(self.data)

        self._world_object: pygfx.Line = pygfx.Line(
            # self.data.feature_data because data is a Buffer
            geometry=pygfx.Geometry(positions=self.data.feature_data, colors=self.colors.feature_data),
            material=material(thickness=size, vertex_colors=True)
        )

        self.world_object.position.z = z_position
