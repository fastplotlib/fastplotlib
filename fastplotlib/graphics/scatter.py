from typing import *

import numpy as np
import pygfx

from ..utils import parse_cmap_values
from ._base import Graphic
from ._features import PointsDataFeature, ColorFeature, CmapFeature, PointsSizesFeature


class ScatterGraphic(Graphic):
    feature_events = ("data", "sizes", "colors", "cmap", "present")

    def __init__(
        self,
        data: np.ndarray,
        sizes: Union[int, float, np.ndarray, list] = 1,
        colors: np.ndarray = "w",
        alpha: float = 1.0,
        cmap: str = None,
        cmap_values: Union[np.ndarray, List] = None,
        z_position: float = 0.0,
        *args,
        **kwargs,
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

        cmap_values: 1D array-like or list of numerical values, optional
            if provided, these values are used to map the colors from the cmap

        alpha: float, optional, default 1.0
            alpha value for the colors

        z_position: float, optional
            z-axis position for placing the graphic

        args
            passed to Graphic

        kwargs
            passed to Graphic

        Features
        --------

        **data**: :class:`.ImageDataFeature`
            Manages the line [x, y, z] positions data buffer, allows regular and fancy indexing.

        **colors**: :class:`.ColorFeature`
            Manages the color buffer, allows regular and fancy indexing.

        **cmap**: :class:`.CmapFeature`
            Manages the cmap, wraps :class:`.ColorFeature` to add additional functionality relevant to cmaps.

        **present**: :class:`.PresentFeature`
            Control the presence of the Graphic in the scene, set to ``True`` or ``False``

        """
        self.data = PointsDataFeature(self, data)
        n_datapoints = self.data().shape[0]

        if cmap is not None:
            colors = parse_cmap_values(
                n_colors=n_datapoints, cmap_name=cmap, cmap_values=cmap_values
            )

        self.colors = ColorFeature(self, colors, n_colors=n_datapoints, alpha=alpha)
        self.cmap = CmapFeature(
            self, self.colors(), cmap_name=cmap, cmap_values=cmap_values
        )

        self.sizes = PointsSizesFeature(self, sizes)
        super(ScatterGraphic, self).__init__(*args, **kwargs)

        world_object = pygfx.Points(
            pygfx.Geometry(positions=self.data(), sizes=self.sizes(), colors=self.colors()),
            material=pygfx.PointsMaterial(color_mode="vertex", vertex_sizes=True),
        )

        self._set_world_object(world_object)

        self.position_z = z_position
