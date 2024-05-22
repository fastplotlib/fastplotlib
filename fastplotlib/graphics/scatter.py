from typing import *

import numpy as np
import pygfx

from ..utils import parse_cmap_values
from ._base import PositionsGraphic
from ._features import PointsSizesFeature, UniformSizes


class ScatterGraphic(PositionsGraphic):
    features = {"data", "sizes", "colors", "cmap"}

    @property
    def sizes(self) -> PointsSizesFeature | float:
        """Get or set the scatter point size(s)"""
        if isinstance(self._sizes, PointsSizesFeature):
            return self._sizes

        elif isinstance(self._sizes, UniformSizes):
            return self._sizes.value

    @sizes.setter
    def sizes(self, value):
        if isinstance(self._sizes, PointsSizesFeature):
            self._sizes[:] = value

        elif isinstance(self._sizes, UniformSizes):
            self._sizes.set_value(self, value)

    def __init__(
        self,
        data: Any,
        colors: str | np.ndarray | tuple[float] | list[float] | list[str] = "w",
        uniform_colors: bool = False,
        alpha: float = 1.0,
        cmap: str = None,
        cmap_values: np.ndarray = None,
        isolated_buffer: bool = True,
        sizes: float | np.ndarray | Iterable[float] = 1,
        uniform_sizes: bool = False,
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

        super().__init__(
            data=data,
            colors=colors,
            uniform_colors=uniform_colors,
            alpha=alpha,
            cmap=cmap,
            cmap_values=cmap_values,
            isolated_buffer=isolated_buffer,
            *args,
            **kwargs
        )

        n_datapoints = self.data.value.shape[0]
        self._sizes = PointsSizesFeature(sizes, n_datapoints=n_datapoints)

        geo_kwargs = {"positions": self._data.buffer}
        material_kwargs = {"pick_write": True}

        if uniform_colors:
            material_kwargs["color_mode"] = "uniform"
            material_kwargs["color"] = self.colors.value
        else:
            material_kwargs["color_mode"] = "vertex"
            geo_kwargs["colors"] = self.colors.buffer

        if uniform_sizes:
            material_kwargs["size_mode"] = "uniform"
            material_kwargs["size"] = self.sizes.value
        else:
            material_kwargs["size_mode"] = "vertex"
            geo_kwargs["sizes"] = self.sizes.buffer

        world_object = pygfx.Points(
            pygfx.Geometry(**geo_kwargs),
            material=pygfx.PointsMaterial(**material_kwargs),
        )

        self._set_world_object(world_object)
