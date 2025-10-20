from typing import *

import numpy as np

import pygfx

from ._positions_base import PositionsGraphic
from .selectors import (
    LinearRegionSelector,
    LinearSelector,
    RectangleSelector,
    PolygonSelector,
)
from .features import (
    Thickness,
    VertexPositions,
    VertexColors,
    UniformColor,
    VertexCmap,
    SizeSpace,
)
from ..utils import quick_min_max


class LineGraphic(PositionsGraphic):
    _features = {
        "data": VertexPositions,
        "colors": (VertexColors, UniformColor),
        "cmap": (VertexCmap, None),  # none if UniformColor
        "thickness": Thickness,
        "size_space": SizeSpace,
    }

    def __init__(
        self,
        data: Any,
        thickness: float = 2.0,
        colors: str | np.ndarray | Sequence = "w",
        uniform_color: bool = False,
        cmap: str = None,
        cmap_transform: np.ndarray | Sequence = None,
        isolated_buffer: bool = True,
        size_space: str = "screen",
        **kwargs,
    ):
        """
        Create a line Graphic, 2d or 3d

        Parameters
        ----------
        data: array-like
            Line data to plot. Can provide 1D, 2D, or a 3D data.
            | If passing a 1D array, it is used to set the y-values and the x-values are generated as an integer range
            from [0, data.size]
            | 2D data must be of shape [n_points, 2]. 3D data must be of shape [n_points, 3]

        thickness: float, optional, default 2.0
            thickness of the line

        colors: str, array, or iterable, default "w"
            specify colors as a single human-readable string, a single RGBA array,
            or a Sequence (array, tuple, or list) of strings or RGBA arrays

        uniform_color: bool, default ``False``
            if True, uses a uniform buffer for the line color,
            basically saves GPU VRAM when the entire line has a single color

        cmap: str, optional
            Apply a colormap to the line instead of assigning colors manually, this
            overrides any argument passed to "colors". For supported colormaps see the
            ``cmap`` library catalogue: https://cmap-docs.readthedocs.io/en/stable/catalog/

        cmap_transform: 1D array-like of numerical values, optional
            if provided, these values are used to map the colors from the cmap

        size_space: str, default "screen"
            coordinate space in which the thickness is expressed ("screen", "world", "model")

        **kwargs
            passed to :class:`.Graphic`

        """

        super().__init__(
            data=data,
            colors=colors,
            uniform_color=uniform_color,
            cmap=cmap,
            cmap_transform=cmap_transform,
            isolated_buffer=isolated_buffer,
            size_space=size_space,
            **kwargs,
        )

        self._thickness = Thickness(thickness)

        if thickness < 1.1:
            MaterialCls = pygfx.LineThinMaterial
            aa = True
        else:
            MaterialCls = pygfx.LineMaterial

        aa = kwargs.get("alpha_mode", "auto") in ("blend", "weighted_blend")

        if uniform_color:
            geometry = pygfx.Geometry(positions=self._data.buffer)
            material = MaterialCls(
                aa=aa,
                thickness=self.thickness,
                color_mode="uniform",
                color=self.colors,
                pick_write=True,
                thickness_space=self.size_space,
                depth_compare="<=",
            )
        else:
            material = MaterialCls(
                aa=aa,
                thickness=self.thickness,
                color_mode="vertex",
                pick_write=True,
                thickness_space=self.size_space,
                depth_compare="<=",
            )
            geometry = pygfx.Geometry(
                positions=self._data.buffer, colors=self._colors.buffer
            )

        world_object: pygfx.Line = pygfx.Line(geometry=geometry, material=material)

        self._set_world_object(world_object)

    @property
    def thickness(self) -> float:
        """Get or set the line thickness"""
        return self._thickness.value

    @thickness.setter
    def thickness(self, value: float):
        self._thickness.set_value(self, value)

    def add_linear_selector(
        self, selection: float = None, axis: str = "x", **kwargs
    ) -> LinearSelector:
        """
        Adds a :class:`.LinearSelector`.

        Selectors are just ``Graphic`` objects, so you can manage, remove, or delete them from a
        plot area just like any other ``Graphic``.

        Parameters
        ----------
        selection: float, optional
            selected point on the linear selector, by default the first datapoint on the line.

        axis: str, default "x"
            axis that the selector resides on

        kwargs
            passed to :class:`.LinearSelector`

        Returns
        -------
        LinearSelector

        """

        bounds_init, limits, size, center = self._get_linear_selector_init_args(
            axis, padding=0
        )

        if selection is None:
            selection = bounds_init[0]

        selector = LinearSelector(
            selection=selection,
            limits=limits,
            axis=axis,
            parent=self,
            **kwargs,
        )

        self._plot_area.add_graphic(selector, center=False)

        return selector

    def add_linear_region_selector(
        self,
        selection: tuple[float, float] = None,
        padding: float = 0.0,
        axis: str = "x",
        **kwargs,
    ) -> LinearRegionSelector:
        """
        Add a :class:`.LinearRegionSelector`.

        Selectors are just ``Graphic`` objects, so you can manage, remove, or delete them from a
        plot area just like any other ``Graphic``.

        Parameters
        ----------
        selection: (float, float), optional
            the starting bounds of the linear region selector, computed from data if not provided

        axis: str, default "x"
            axis that the selector resides on

        padding: float, default 0.0
            Extra padding to extend the linear region selector along the orthogonal axis to make it easier to interact with.

        kwargs
            passed to ``LinearRegionSelector``

        Returns
        -------
        LinearRegionSelector
            linear selection graphic

        """

        bounds_init, limits, size, center = self._get_linear_selector_init_args(
            axis, padding
        )

        if selection is None:
            selection = bounds_init

        # create selector
        selector = LinearRegionSelector(
            selection=selection,
            limits=limits,
            size=size,
            center=center,
            axis=axis,
            parent=self,
            **kwargs,
        )

        self._plot_area.add_graphic(selector, center=False)

        # PlotArea manages this for garbage collection etc. just like all other Graphics
        # so we should only work with a proxy on the user-end
        return selector

    def add_rectangle_selector(
        self,
        selection: tuple[float, float, float, float] = None,
        **kwargs,
    ) -> RectangleSelector:
        """
        Add a :class:`.RectangleSelector`.

        Selectors are just ``Graphic`` objects, so you can manage, remove, or delete them from a
        plot area just like any other ``Graphic``.

        Parameters
        ----------
        selection: (float, float, float, float), optional
            initial (xmin, xmax, ymin, ymax) of the selection
        """
        # computes args to create selectors
        n_datapoints = self.data.value.shape[0]
        value_25p = int(n_datapoints / 4)

        # remove any nans
        data = self.data.value[~np.any(np.isnan(self.data.value), axis=1)]

        x_axis_vals = data[:, 0]
        y_axis_vals = data[:, 1]

        ymin = np.floor(y_axis_vals.min()).astype(int)
        ymax = np.ceil(y_axis_vals.max()).astype(int)

        # default selection is 25% of the image
        if selection is None:
            selection = (x_axis_vals[0], x_axis_vals[value_25p], ymin, ymax)

        # min/max limits
        limits = (x_axis_vals[0], x_axis_vals[-1], ymin * 1.5, ymax * 1.5)

        selector = RectangleSelector(
            selection=selection,
            limits=limits,
            parent=self,
            **kwargs,
        )

        self._plot_area.add_graphic(selector, center=False)

        return selector

    def add_polygon_selector(
        self,
        selection: List[tuple[float, float]] = None,
        **kwargs,
    ) -> PolygonSelector:
        """
        Add a :class:`.PolygonSelector`.

        Selectors are just ``Graphic`` objects, so you can manage, remove, or delete them from a
        plot area just like any other ``Graphic``.

        Parameters
        ----------
        selection: List of positions, optional
            Initial points for the polygon. If not given or None, you'll start drawing the selection (clicking adds points to the polygon).
        """

        # remove any nans
        data = self.data.value[~np.any(np.isnan(self.data.value), axis=1)]

        x_axis_vals = data[:, 0]
        y_axis_vals = data[:, 1]

        ymin = np.floor(y_axis_vals.min()).astype(int)
        ymax = np.ceil(y_axis_vals.max()).astype(int)

        # min/max limits
        limits = (x_axis_vals[0], x_axis_vals[-1], ymin * 1.5, ymax * 1.5)

        selector = PolygonSelector(
            selection,
            limits,
            parent=self,
            **kwargs,
        )

        self._plot_area.add_graphic(selector, center=False)

        return selector

    # TODO: this method is a bit of a mess, can refactor later
    def _get_linear_selector_init_args(
        self, axis: str, padding
    ) -> tuple[tuple[float, float], tuple[float, float], float, float]:
        # computes args to create selectors
        n_datapoints = self.data.value.shape[0]
        value_25p = int(n_datapoints / 4)

        # remove any nans
        data = self.data.value[~np.any(np.isnan(self.data.value), axis=1)]

        if axis == "x":
            # xvals
            axis_vals = data[:, 0]

            # yvals to get size and center
            magn_vals = data[:, 1]
        elif axis == "y":
            axis_vals = data[:, 1]
            magn_vals = data[:, 0]

        bounds_init = axis_vals[0], axis_vals[value_25p]
        limits = axis_vals[0], axis_vals[-1]

        # width or height of selector
        size = int(np.ptp(magn_vals) * 1.5 + padding)

        # center of selector along the other axis
        center = sum(quick_min_max(magn_vals)) / 2

        return bounds_init, limits, size, center
