from typing import *
from warnings import warn

import numpy as np
import cmap as cmap_lib

import pygfx

from .selectors import (
    LinearRegionSelector,
    LinearSelector,
    RectangleSelector,
    PolygonSelector,
)
from .features import (
    Thickness,
    DashPattern,
    parse_dash_pattern,
    VertexPositions,
    VertexColors,
    UniformColor,
    VertexCmap,
    SizeSpace,
)
from features.types import ColorLike, MultiColorLike
from ..utils import quick_min_max
from ._positions_base import PositionsGraphic, VALID_COLOR_MODES
from features.types import ColorLike, MultiColorLike

class LineGraphic(PositionsGraphic):
    _features = {
        "data": VertexPositions,
        "colors": (VertexColors, UniformColor),
        "cmap": (VertexCmap, None),  # none if UniformColor
        "thickness": Thickness,
        "size_space": SizeSpace,
        "dash_pattern": DashPattern,
    }

    def __init__(
        self,
        data: Any,
        thickness: float = 2.0,
        colors: str | ColorLike | MultiColorLike = "w",
        cmap: cmap_lib.ColormapLike | None = None,
        cmap_transform: np.ndarray | None = None,
        color_mode: Literal["auto", "uniform", "vertex", "vertex_map"] = "auto",
        size_space: str = "screen",
        dash_pattern: str | tuple | list = (),
        thin: bool = False,
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

        colors: str, ColorLike or MultiColorLike, default "w"
            specify colors as a single human-readable string, a single RGBA array,
            or a Sequence (array, tuple, or list) of strings or RGBA arrays

        cmap: cmap_lib.ColormapLike, optional
            Apply a colormap to the line instead of assigning colors manually, this
            overrides any argument passed to "colors". For supported colormaps see the
            ``cmap`` library catalogue: https://cmap-docs.readthedocs.io/en/stable/catalog/

        color_mode: one of "auto", "uniform", "vertex", "vertex_map", default "auto"
            "uniform" restricts to a single color for all line datapoints.
            "vertex" allows independent colors per vertex.
            "vertex_map" uses the ``cmap`` to set per-vertex colors.
            For most cases you can keep it as "auto" and the `color_mode` is determineed automatically based on the
            argument passed to `colors`. if `colors` represents a single color, then the mode is set to "uniform".
            If `colors` represents a unique color per-datapoint, or if a cmap is provided, then `color_mode` is set to
            "vertex_map". You can switch between color_modes after creating the graphic.

        cmap_transform: 1D array-like of numerical values, optional
            if provided, these values are used to map the colors from the cmap

        size_space: str, default "screen"
            coordinate space in which the thickness is expressed ("screen", "world", "model")

        dash_pattern: str, tuple, or list, default ()
            The dash pattern. May be a matplotlib-style string, one of ``"-", "--", "-.", ":"``
            or ``"solid", "dashed", "dashdot", "dotted"``, or a sequence of floats describing the
            length of strokes and gaps. Ignored when ``thin`` is True.

        thin: bool, default False
            Use the more performant thin line material, which is always one physical pixel wide.
            Thickness, dashing, and anti-aliasing are ignored when True.

        **kwargs
            passed to :class:`.Graphic`

        """

        super().__init__(
            data=data,
            colors=colors,
            cmap=cmap,
            cmap_transform=cmap_transform,
            color_mode=color_mode,
            size_space=size_space,
            **kwargs,
        )

        self._thickness = Thickness(thickness)
        self._dash_pattern = DashPattern(dash_pattern)
        self._thin = bool(thin)

        if self._thin and parse_dash_pattern(dash_pattern):
            warn(
                "`dash_pattern` is ignored when `thin=True`; the thin line material does not "
                "support dashing"
            )

        world_object = pygfx.Line(
            geometry=self._make_geo(),
            material=self._make_material(),
        )

        self._set_world_object(world_object)

    def _get_material_kwargs(self) -> dict:
        # pygfx line material kwargs assembled from the current feature state
        kwargs = dict(
            thickness=self.thickness,
            thickness_space=self.size_space,
            dash_pattern=parse_dash_pattern(self._dash_pattern.value),
            aa=self.alpha_mode in ("blend", "weighted_blend"),
            pick_write=True,
            depth_compare="<=",
        )

        if self._cmap is not None:
            kwargs["color_mode"] = "vertex_map"
            kwargs["map"] = self.cmap.to_pygfx()
        elif isinstance(self._colors, UniformColor):
            kwargs["color_mode"] = "uniform"
            kwargs["color"] = self.colors
        else:
            kwargs["color_mode"] = "vertex"

        return kwargs

    def _get_geo_kwargs(self) -> dict:
        kwargs = dict(
            positions=self._data._fpl_buffer
        )

        if self._cmap is not None:
            # cmap overrides all
            kwargs["texcoords"] = pygfx.Buffer(self._cmap_transform.value)

        elif isinstance(self._colors, VertexColors):
            # per-vertex colors
            kwargs["colors"] = self._colors._fpl_buffer

        # no additional kwargs for uniform color

        return kwargs

    def _make_material(self) -> pygfx.LineMaterial:
        # create the pygfx material, subclasses override to use a different line material
        material_cls = pygfx.LineThinMaterial if self._thin else pygfx.LineMaterial
        return material_cls(**self._get_material_kwargs())

    def _make_geo(self) -> pygfx.Geometry:
        kwargs = self._get_geo_kwargs()
        return pygfx.Geometry(**kwargs)

    @property
    def thickness(self) -> float:
        """Get or set the line thickness"""
        return self._thickness.value

    @thickness.setter
    def thickness(self, value: float):
        self._thickness.set_value(self, value)

    @property
    def dash_pattern(self) -> str | tuple | list:
        """
        Get or set the dash pattern.

        May be a matplotlib-style string, one of ``"-", "--", "-.", ":"`` or
        ``"solid", "dashed", "dashdot", "dotted"``, or a sequence of floats describing the
        length of strokes and gaps. Ignored when ``thin`` is True.
        """
        return self._dash_pattern.value

    @dash_pattern.setter
    def dash_pattern(self, value: str | tuple | list):
        if self._thin and parse_dash_pattern(value):
            warn(
                "`dash_pattern` is ignored when `thin=True`; the thin line material does not "
                "support dashing"
            )
        self._dash_pattern.set_value(self, value)

    @property
    def thin(self) -> bool:
        """
        Get or set whether the line uses the more performant thin line material, which is
        always one physical pixel wide. Thickness, dashing, and anti-aliasing are ignored
        when True.
        """
        return self._thin

    @thin.setter
    def thin(self, value: bool):
        value = bool(value)
        if value == self._thin:
            return

        if value and parse_dash_pattern(self._dash_pattern.value):
            warn(
                "`dash_pattern` is ignored when `thin=True`; the thin line material does not "
                "support dashing"
            )

        self._thin = value

        # thin vs. non-thin is a different pygfx material, so rebuild and swap it in place,
        # keeping the same geometry
        material = self._make_material()
        material.opacity = self.alpha
        material.alpha_mode = self.alpha_mode
        self.world_object.material = material

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
        selection: list[tuple[float, float]], optional
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
