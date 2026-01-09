from typing import Any, Sequence

import numpy as np

import pygfx
from ._base import Graphic
from .selectors import LinearRegionSelector, LinearSelector, RectangleSelector
from ..utils import quick_min_max
from .features import (
    VertexPositions,
    VertexColors,
    UniformColor,
    VertexCmap,
    SizeSpace,
)


class PositionsGraphic(Graphic):
    """Base class for LineGraphic and ScatterGraphic"""

    @property
    def data(self) -> VertexPositions:
        """Get or set the graphic's data"""
        return self._data

    @data.setter
    def data(self, value):
        self._data[:] = value

    @property
    def colors(self) -> VertexColors | pygfx.Color:
        """Get or set the colors"""
        if isinstance(self._colors, VertexColors):
            return self._colors

        elif isinstance(self._colors, UniformColor):
            return self._colors.value

    @colors.setter
    def colors(self, value: str | np.ndarray | Sequence[float] | Sequence[str]):
        if isinstance(self._colors, VertexColors):
            self._colors[:] = value

        elif isinstance(self._colors, UniformColor):
            self._colors.set_value(self, value)

    @property
    def cmap(self) -> VertexCmap:
        """
        Control the cmap or cmap transform

        For supported colormaps see the ``cmap`` library catalogue: https://cmap-docs.readthedocs.io/en/stable/catalog/
        """
        return self._cmap

    @cmap.setter
    def cmap(self, name: str):
        if self._cmap is None:
            raise BufferError("Cannot use cmap with uniform_colors=True")

        self._cmap[:] = name

    @property
    def size_space(self):
        """
        The coordinate space in which the size is expressed ('screen', 'world', 'model')

        See https://docs.pygfx.org/stable/_autosummary/utils/utils/enums/pygfx.utils.enums.CoordSpace.html#pygfx.utils.enums.CoordSpace for available options.
        """
        return self._size_space.value

    @size_space.setter
    def size_space(self, value: str):
        self._size_space.set_value(self, value)

    def __init__(
        self,
        data: Any,
        colors: str | np.ndarray | tuple[float] | list[float] | list[str] = "w",
        uniform_color: bool = False,
        cmap: str | VertexCmap = None,
        cmap_transform: np.ndarray = None,
        isolated_buffer: bool = True,
        size_space: str = "screen",
        *args,
        **kwargs,
    ):
        if isinstance(data, VertexPositions):
            self._data = data
        else:
            self._data = VertexPositions(data, isolated_buffer=isolated_buffer)

        if cmap_transform is not None and cmap is None:
            raise ValueError("must pass `cmap` if passing `cmap_transform`")

        if cmap is not None:
            # if a cmap is specified it overrides colors argument
            if uniform_color:
                raise TypeError("Cannot use cmap if uniform_color=True")

            if isinstance(cmap, str):
                # make colors from cmap
                if isinstance(colors, VertexColors):
                    # share buffer with existing colors instance for the cmap
                    self._colors = colors
                    self._colors._shared += 1
                else:
                    # create vertex colors buffer
                    self._colors = VertexColors("w", n_colors=self._data.value.shape[0])
                    # make cmap using vertex colors buffer
                    self._cmap = VertexCmap(
                        self._colors,
                        cmap_name=cmap,
                        transform=cmap_transform,
                    )
            elif isinstance(cmap, VertexCmap):
                # use existing cmap instance
                self._cmap = cmap
                self._colors = cmap._vertex_colors
            else:
                raise TypeError(
                    "`cmap` argument must be a <str> cmap name or an existing `VertexCmap` instance"
                )
        else:
            # no cmap given
            if isinstance(colors, VertexColors):
                # share buffer with existing colors instance
                self._colors = colors
                self._colors._shared += 1
                # blank colormap instance
                self._cmap = VertexCmap(self._colors, cmap_name=None, transform=None)
            else:
                if uniform_color:
                    if not isinstance(colors, str):  # not a single color
                        if not len(colors) in [3, 4]:  # not an RGB(A) array
                            raise TypeError(
                                "must pass a single color if using `uniform_colors=True`"
                            )
                    self._colors = UniformColor(colors)
                    self._cmap = None
                else:
                    self._colors = VertexColors(
                        colors, n_colors=self._data.value.shape[0]
                    )
                    self._cmap = VertexCmap(
                        self._colors, cmap_name=None, transform=None
                    )

        self._size_space = SizeSpace(size_space)
        super().__init__(*args, **kwargs)

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

        # place selector above this graphic
        selector.offset = selector.offset + (0.0, 0.0, self.offset[-1] + 1)

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

        # place selector below this graphic
        selector.offset = selector.offset + (0.0, 0.0, self.offset[-1] - 1)

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

        # remove any nans
        data = self.data.value[~np.any(np.isnan(self.data.value), axis=1)]

        x_axis_vals = data[:, 0]
        y_axis_vals = data[:, 1]

        ymin = np.floor(y_axis_vals.min()).astype(int)
        ymax = np.ceil(y_axis_vals.max()).astype(int)
        y25p = 0.25 * (ymax - ymin)
        xmin = np.floor(x_axis_vals.min()).astype(int)
        xmax = np.ceil(x_axis_vals.max()).astype(int)
        x25p = 0.25 * (xmax - xmin)

        # default selection is 25% of the image
        if selection is None:
            selection = (xmin, xmin + x25p, ymin, ymax)

        # min/max limits include the data + 25% padding in the y-direction
        limits = (xmin, xmax, ymin - y25p, ymax + y25p)

        selector = RectangleSelector(
            selection=selection,
            limits=limits,
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

        axis_vals_min = np.floor(axis_vals.min()).astype(int)
        axis_vals_max = np.ceil(axis_vals.max()).astype(int)
        axis_vals_25p = axis_vals_min + 0.25 * (axis_vals_max - axis_vals_min)

        # default selection is 25% of the image
        bounds_init = axis_vals_min, axis_vals_25p
        limits = axis_vals_min, axis_vals_max

        # width or height of selector
        size = int(np.ptp(magn_vals) * 1.5 + padding)

        # center of selector along the other axis
        center = sum(quick_min_max(magn_vals)) / 2

        return bounds_init, limits, size, center
