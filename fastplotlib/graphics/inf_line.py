from typing import *

import numpy as np

import pygfx

from .line import LineGraphic
from .features import (
    InfLineAxisData,
    InfLineColors,
    UniformColor,
    VertexCmap,
    Thickness,
    SizeSpace,
    DashPattern,
)


class InfLineGraphic(LineGraphic):
    _features = {
        "data": InfLineAxisData,
        "colors": (InfLineColors, UniformColor),
        "cmap": (VertexCmap, None),  # none if UniformColor
        "thickness": Thickness,
        "size_space": SizeSpace,
        "dash_pattern": DashPattern,
    }

    # one color per line, each broadcast to the two vertices of the line's segment
    _VertexColorsCls = InfLineColors

    def __init__(
        self,
        data: Any,
        axis: Literal["x", "y", "z"] | None = None,
        thickness: float = 2.0,
        colors: str | np.ndarray | Sequence = "w",
        cmap: str = None,
        cmap_transform: np.ndarray | Sequence = None,
        color_mode: Literal["auto", "uniform", "vertex"] = "auto",
        start_is_infinite: bool = True,
        end_is_infinite: bool = True,
        dash_pattern: str | tuple | list = (),
        size_space: str = "screen",
        **kwargs,
    ):
        """
        Create a collection of infinite lines.

        Parameters
        ----------
        data: array-like
            The line positions. If ``axis`` is "x", "y", or "z", a 1D array of positions along
            that axis; one infinite line is drawn at each position. If ``axis`` is None, ``data``
            is used directly as the segment endpoints, of shape [n_points, 2 | 3], where every two
            consecutive points define one line.

        axis: "x", "y", "z", or None, default None
            The axis along which the line positions are given. If None, ``data`` is interpreted
            directly as the segment endpoints.

        thickness: float, optional, default 2.0
            thickness of the lines

        colors: str, array, or iterable, default "w"
            specify colors as a single human-readable string, a single RGBA array, or a Sequence
            (array, tuple, or list) of strings or RGBA arrays. A sequence of colors provides one
            color per line.

        cmap: str, optional
            Apply a colormap to the lines instead of assigning colors manually, one color per line.
            This overrides any argument passed to "colors". For supported colormaps see the
            ``cmap`` library catalogue: https://cmap-docs.readthedocs.io/en/stable/catalog/

        color_mode: one of "auto", "uniform", "vertex", default "auto"
            "uniform" restricts to a single color for all lines.
            "vertex" allows an independent color per line.
            For most cases you can keep it as "auto" and the `color_mode` is determined automatically
            based on the argument passed to `colors`.

        cmap_transform: 1D array-like of numerical values, optional
            if provided, these values are used to map the colors from the cmap

        start_is_infinite: bool, default True
            whether the start of each line is extended to infinity

        end_is_infinite: bool, default True
            whether the end of each line is extended to infinity

        dash_pattern: str, tuple, or list, default ()
            The dash pattern. May be a matplotlib-style string, one of ``"-", "--", "-.", ":"``
            or ``"solid", "dashed", "dashdot", "dotted"``, or a sequence of floats describing the
            length of strokes and gaps.

        size_space: str, default "screen"
            coordinate space in which the thickness is expressed ("screen", "world", "model")

        **kwargs
            passed to :class:`.Graphic`

        """

        self._start_is_infinite = bool(start_is_infinite)
        self._end_is_infinite = bool(end_is_infinite)

        data = InfLineAxisData(data, axis=axis)

        super().__init__(
            data=data,
            thickness=thickness,
            colors=colors,
            cmap=cmap,
            cmap_transform=cmap_transform,
            color_mode=color_mode,
            size_space=size_space,
            dash_pattern=dash_pattern,
            thin=False,
            **kwargs,
        )

    def _make_material(self) -> pygfx.LineInfiniteSegmentMaterial:
        return pygfx.LineInfiniteSegmentMaterial(
            start_is_infinite=self._start_is_infinite,
            end_is_infinite=self._end_is_infinite,
            **self._material_kwargs(),
        )

    @property
    def axis(self) -> str | None:
        """the axis the lines are defined along ("x", "y", "z"), or None if set from endpoints"""
        return self._data.axis

    @property
    def start_is_infinite(self) -> bool:
        """Get or set whether the start of each line is extended to infinity"""
        return self._start_is_infinite

    @start_is_infinite.setter
    def start_is_infinite(self, value: bool):
        self._start_is_infinite = bool(value)
        self.world_object.material.start_is_infinite = self._start_is_infinite

    @property
    def end_is_infinite(self) -> bool:
        """Get or set whether the end of each line is extended to infinity"""
        return self._end_is_infinite

    @end_is_infinite.setter
    def end_is_infinite(self, value: bool):
        self._end_is_infinite = bool(value)
        self.world_object.material.end_is_infinite = self._end_is_infinite

    @property
    def thin(self) -> bool:
        """infinite lines do not support the thin line material"""
        return False

    @thin.setter
    def thin(self, value: bool):
        if value:
            raise NotImplementedError(
                "`InfLineGraphic` does not support the thin line material"
            )

    def _selectors_not_supported(self, *args, **kwargs):
        raise NotImplementedError("selectors are not supported on `InfLineGraphic`")

    add_linear_selector = _selectors_not_supported
    add_linear_region_selector = _selectors_not_supported
    add_rectangle_selector = _selectors_not_supported
    add_polygon_selector = _selectors_not_supported

    def format_pick_info(self, pick_info: dict) -> str:
        # two vertices per line
        index = pick_info["vertex_index"] // 2

        if self.axis is not None:
            return f"{self.axis}: {self.data.value[index]:.4g}"

        # for axis=None, show the first endpoint of the picked line
        point = self.data.value[index][0]
        return "\n".join(f"{dim}: {val:.4g}" for dim, val in zip("xyz", point))
