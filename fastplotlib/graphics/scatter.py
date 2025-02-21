from typing import *

import numpy as np
import pygfx

from ._positions_base import PositionsGraphic
from ._features import PointsSizesFeature, UniformSize, SizeSpace


class ScatterGraphic(PositionsGraphic):
    _features = {"data", "sizes", "colors", "cmap", "size_space"}

    def __init__(
        self,
        data: Any,
        colors: str | np.ndarray | tuple[float] | list[float] | list[str] = "w",
        uniform_color: bool = False,
        alpha: float = 1.0,
        cmap: str = None,
        cmap_transform: np.ndarray = None,
        isolated_buffer: bool = True,
        sizes: float | np.ndarray | Iterable[float] = 1,
        uniform_size: bool = False,
        size_space: str = "screen",
        **kwargs,
    ):
        """
        Create a Scatter Graphic, 2d or 3d

        Parameters
        ----------
        data: array-like
            Scatter data to plot, 2D must be of shape [n_points, 2], 3D must be of shape [n_points, 3]

        colors: str, array, or iterable, default "w"
            specify colors as a single human readable string, a single RGBA array,
            or an iterable of strings or RGBA arrays

        uniform_color: bool, default False
            if True, uses a uniform buffer for the scatter point colors,
            basically saves GPU VRAM when the entire line has a single color

        alpha: float, optional, default 1.0
            alpha value for the colors

        cmap: str, optional
            apply a colormap to the scatter instead of assigning colors manually, this
            overrides any argument passed to "colors"

        cmap_transform: 1D array-like or list of numerical values, optional
            if provided, these values are used to map the colors from the cmap

        isolated_buffer: bool, default True
            whether the buffers should be isolated from the user input array.
            Generally always ``True``, ``False`` is for rare advanced use.

        sizes: float or iterable of float, optional, default 1.0
            size of the scatter points

        uniform_size: bool, default False
            if True, uses a uniform buffer for the scatter point sizes,
            basically saves GPU VRAM when all scatter points are the same size

        size_space: str, default "screen"
            coordinate space in which the size is expressed ("screen", "world", "model")

        kwargs
            passed to Graphic

        """

        super().__init__(
            data=data,
            colors=colors,
            uniform_color=uniform_color,
            alpha=alpha,
            cmap=cmap,
            cmap_transform=cmap_transform,
            isolated_buffer=isolated_buffer,
            size_space=size_space,
            **kwargs,
        )

        n_datapoints = self.data.value.shape[0]

        geo_kwargs = {"positions": self._data.buffer}
        material_kwargs = {"pick_write": True}
        self._size_space = SizeSpace(size_space)

        if uniform_color:
            material_kwargs["color_mode"] = "uniform"
            material_kwargs["color"] = self.colors
        else:
            material_kwargs["color_mode"] = "vertex"
            geo_kwargs["colors"] = self.colors.buffer

        if uniform_size:
            material_kwargs["size_mode"] = "uniform"
            self._sizes = UniformSize(sizes)
            material_kwargs["size"] = self.sizes
        else:
            material_kwargs["size_mode"] = "vertex"
            self._sizes = PointsSizesFeature(sizes, n_datapoints=n_datapoints)
            geo_kwargs["sizes"] = self.sizes.buffer

        material_kwargs["size_space"] = self.size_space
        world_object = pygfx.Points(
            pygfx.Geometry(**geo_kwargs),
            material=pygfx.PointsMaterial(**material_kwargs),
        )

        self._set_world_object(world_object)

    @property
    def sizes(self) -> PointsSizesFeature | float:
        """Get or set the scatter point size(s)"""
        if isinstance(self._sizes, PointsSizesFeature):
            return self._sizes

        elif isinstance(self._sizes, UniformSize):
            return self._sizes.value

    @sizes.setter
    def sizes(self, value):
        if isinstance(self._sizes, PointsSizesFeature):
            self._sizes[:] = value

        elif isinstance(self._sizes, UniformSize):
            self._sizes.set_value(self, value)
