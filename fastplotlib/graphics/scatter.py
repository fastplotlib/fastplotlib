from typing import *

import numpy as np
import pygfx

from ..utils import parse_cmap_values
from ._base import PositionsGraphic
from ._features import PointsDataFeature, ColorFeature, CmapFeature, PointsSizesFeature


class ScatterGraphic(PositionsGraphic):
    features = {"data", "sizes", "colors"}#, "cmap", "present"}

    def __init__(
        self,
        data: np.ndarray,
        sizes: float | np.ndarray | Iterable[float] = 1,
        colors: str | np.ndarray | Iterable[str] = "w",
        alpha: float = 1.0,
        cmap: str = None,
        cmap_values: np.ndarray | List = None,
        z_position: float = 0.0,
        isolated_buffer: bool = True,
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
        self._data = PointsDataFeature(data, isolated_buffer=isolated_buffer)

        n_datapoints = self._data.value.shape[0]

        if cmap is not None:
            colors = parse_cmap_values(
                n_colors=n_datapoints, cmap_name=cmap, cmap_values=cmap_values
            )

        if isinstance(colors, ColorFeature):
            self._colors = colors
            self._colors._shared += 1
        else:
            self._colors = ColorFeature(
                colors,
                n_colors=self._data.value.shape[0],
                alpha=alpha,
            )

        # self.cmap = CmapFeature(
        #     self, self.colors(), cmap_name=cmap, cmap_values=cmap_values
        # )

        self._sizes = PointsSizesFeature(sizes, n_datapoints=n_datapoints)
        super().__init__(*args, **kwargs)

        world_object = pygfx.Points(
            pygfx.Geometry(
                positions=self._data.buffer, sizes=self._sizes.buffer, colors=self._colors.buffer
            ),
            material=pygfx.PointsMaterial(
                color_mode="vertex", size_mode="vertex", pick_write=True
            ),
        )

        self._set_world_object(world_object)

        self.position_z = z_position
