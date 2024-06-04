from typing import *
import weakref

import numpy as np

import pygfx

from ._base import PositionsGraphic
from .selectors import LinearRegionSelector, LinearSelector
from ._features import Thickness


class LineGraphic(PositionsGraphic):
    features = {"data", "colors", "cmap", "thickness"}

    @property
    def thickness(self) -> float:
        """Graphic name"""
        return self._thickness.value

    @thickness.setter
    def thickness(self, value: float):
        self._thickness.set_value(self, value)

    def __init__(
        self,
        data: Any,
        thickness: float = 2.0,
        colors: str | np.ndarray | Iterable = "w",
        uniform_colors: bool = False,
        alpha: float = 1.0,
        cmap: str = None,
        cmap_values: np.ndarray | Iterable = None,
        isolated_buffer: bool = True,
        **kwargs,
    ):
        """
        Create a line Graphic, 2d or 3d

        Parameters
        ----------
        data: array-like
            Line data to plot, 2D must be of shape [n_points, 2], 3D must be of shape [n_points, 3]

        thickness: float, optional, default 2.0
            thickness of the line

        colors: str, array, or iterable, default "w"
            specify colors as a single human-readable string, a single RGBA array,
            or an iterable of strings or RGBA arrays

        cmap: str, optional
            apply a colormap to the line instead of assigning colors manually, this
            overrides any argument passed to "colors"

        cmap_values: 1D array-like or Iterable of numerical values, optional
            if provided, these values are used to map the colors from the cmap

        alpha: float, optional, default 1.0
            alpha value for the colors

        z_position: float, optional
            z-axis position for placing the graphic

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

        **thickness**: :class:`.ThicknessFeature`
            Manages the thickness feature of the lines.

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
            **kwargs,
        )

        self._thickness = Thickness(thickness)

        if thickness < 1.1:
            MaterialCls = pygfx.LineThinMaterial
        else:
            MaterialCls = pygfx.LineMaterial

        if uniform_colors:
            geometry = pygfx.Geometry(positions=self._data.buffer)
            material = MaterialCls(
                thickness=self.thickness, color_mode="uniform", pick_write=True
            )
        else:
            material = MaterialCls(
                thickness=self.thickness, color_mode="vertex", pick_write=True
            )
            geometry = pygfx.Geometry(
                positions=self._data.buffer, colors=self._colors.buffer
            )

        world_object: pygfx.Line = pygfx.Line(geometry=geometry, material=material)

        self._set_world_object(world_object)

    def add_linear_selector(
        self, selection: float = None, padding: float = 0.0, axis: str = "x", **kwargs
    ) -> LinearSelector:
        """
        Adds a linear selector.

        Parameters
        ----------
        selection: float
            initial position of the selector

        padding: float
            pad the length of the selector

        kwargs
            passed to :class:`.LinearSelector`

        Returns
        -------
        LinearSelector

        """

        data = self.data.value[~np.any(np.isnan(self.data.value), axis=1)]

        if axis == "x":
            # xvals
            axis_vals = data[:, 0]

            # yvals to get size and center
            magn_vals = data[:, 1]
        elif axis == "y":
            axis_vals = data[:, 1]
            magn_vals = data[:, 0]

        if selection is None:
            selection = axis_vals[0]
        limits = axis_vals[0], axis_vals[-1]

        if not limits[0] <= selection <= limits[1]:
            raise ValueError(
                f"the passed selection: {selection} is beyond the limits: {limits}"
            )

        # width or height of selector
        size = int(np.ptp(magn_vals) * 1.5 + padding)

        # center of selector along the other axis
        center = np.nanmean(magn_vals)

        selector = LinearSelector(
            selection=selection,
            limits=limits,
            size=size,
            center=center,
            axis=axis,
            parent=weakref.proxy(self),
            **kwargs,
        )

        self._plot_area.add_graphic(selector, center=False)

        # place selector above this graphic
        selector.offset = selector.offset + (0.0, 0.0, self.offset[-1] + 1)

        return weakref.proxy(selector)

    def add_linear_region_selector(
        self, padding: float = 0.0, axis: str = "x", **kwargs
    ) -> LinearRegionSelector:
        """
        Add a :class:`.LinearRegionSelector`. Selectors are just ``Graphic`` objects, so you can manage,
        remove, or delete them from a plot area just like any other ``Graphic``.

        Parameters
        ----------
        padding: float, default 100.0
            Extends the linear selector along the y-axis to make it easier to interact with.

        kwargs
            passed to ``LinearRegionSelector``

        Returns
        -------
        LinearRegionSelector
            linear selection graphic

        """

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
        center = np.nanmean(magn_vals)

        # create selector
        selector = LinearRegionSelector(
            selection=bounds_init,
            limits=limits,
            size=size,
            center=center,
            axis=axis,
            parent=weakref.proxy(self),
            **kwargs,
        )

        self._plot_area.add_graphic(selector, center=False)

        # place selector below this graphic
        selector.offset = selector.offset + (0.0, 0.0, self.offset[-1] - 1)

        # PlotArea manages this for garbage collection etc. just like all other Graphics
        # so we should only work with a proxy on the user-end
        return weakref.proxy(selector)

    # TODO: this method is a bit of a mess, can refactor later
    def _get_linear_selector_init_args(self, padding: float, **kwargs):
        # computes initial bounds, limits, size and origin of linear selectors
        data = self.data.value

        if "axis" in kwargs.keys():
            axis = kwargs["axis"]
        else:
            axis = "x"

        if axis == "x":
            offset = self.offset[0]
            # x limits
            limits = (data[0, 0] + offset, data[-1, 0] + offset)

            # height + padding
            size = np.ptp(data[:, 1]) + padding

            # initial position of the selector
            position_y = (data[:, 1].min() + data[:, 1].max()) / 2

            # need y offset too for this
            origin = (limits[0] - offset, position_y + self.offset[1])

            # endpoints of the data range
            # used by linear selector but not linear region
            end_points = (
                self.data.value[:, 1].min() - padding,
                self.data.value[:, 1].max() + padding,
            )
        else:
            offset = self.offset[1]
            # y limits
            limits = (data[0, 1] + offset, data[-1, 1] + offset)

            # width + padding
            size = np.ptp(data[:, 0]) + padding

            # initial position of the selector
            position_x = (data[:, 0].min() + data[:, 0].max()) / 2

            # need x offset too for this
            origin = (position_x + self.offset[0], limits[0] - offset)

            end_points = (
                self.data.value[:, 0].min() - padding,
                self.data.value[:, 0].max() + padding,
            )

        # initial bounds are 20% of the limits range
        bounds_init = (limits[0], int(np.ptp(limits) * 0.2) + offset)

        return bounds_init, limits, size, origin, axis, end_points
