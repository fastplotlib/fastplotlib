from typing import *

import numpy as np
import pygfx

from ._base import Graphic
from .features import PointsDataFeature, ColorFeature, CmapFeature
from ..utils import make_colors


class ScatterGraphic(Graphic):
    def __init__(
            self,
            data: np.ndarray,
            sizes: Union[int, np.ndarray, list] = 1,
            colors: np.ndarray = "w",
            alpha: float = 1.0,
            cmap: str = None,
            z_position: float = 0.0,
            *args,
            **kwargs
    ):
        """
        Create a Scatter Graphic, 2d or 3d

        Parameters
        ----------
        data: array-like
            Scatter data to plot, 2D must be of shape [n_points, 2], 3D must be of shape [n_points, 3]

        sizes: float or iterable of float, optional, default 1.0
            size of the scatter points

        colors: str, array, or iterable, default "w"
            specify colors as a single human readable string, a single RGBA array,
            or an iterable of strings or RGBA arrays

        cmap: str, optional
            apply a colormap to the scatter instead of assigning colors manually, this
            overrides any argument passed to "colors"

        alpha: float, optional, default 1.0
            alpha value for the colors

        z_position: float, optional
            z-axis position for placing the graphic

        args
            passed to Graphic

        kwargs
            passed to Graphic

        """
        self.data = PointsDataFeature(self, data)

        if cmap is not None:
            colors = make_colors(n_colors=self.data().shape[0], cmap=cmap, alpha=alpha)

        self.colors = ColorFeature(self, colors, n_colors=self.data().shape[0], alpha=alpha)
        self.cmap = CmapFeature(self, self.colors())

        if isinstance(sizes, int):
            sizes = np.full(self.data().shape[0], sizes, dtype=np.float32)
        elif isinstance(sizes, np.ndarray):
            if (sizes.ndim != 1) or (sizes.size != self.data().shape[0]):
                raise ValueError(f"numpy array of `sizes` must be 1 dimensional with "
                                 f"the same length as the number of datapoints")
        elif isinstance(sizes, list):
            if len(sizes) != self.data().shape[0]:
                raise ValueError("list of `sizes` must have the same length as the number of datapoints")

        super(ScatterGraphic, self).__init__(*args, **kwargs)

        self._world_object: pygfx.Points = pygfx.Points(
            pygfx.Geometry(positions=self.data(), sizes=sizes, colors=self.colors()),
            material=pygfx.PointsMaterial(vertex_colors=True, vertex_sizes=True)
        )

        self.world_object.position.z = z_position
