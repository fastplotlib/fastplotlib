from typing import *
import weakref

import numpy as np
import pygfx

from ._base import Graphic, Interaction, PreviouslyModifiedData
from .features import PointsDataFeature, ColorFeature, CmapFeature, ThicknessFeature
from .selectors import LinearRegionSelector, LinearSelector
from ..utils import parse_cmap_values


class LineGraphic(Graphic, Interaction):
    feature_events = (
        "data",
        "colors",
        "cmap",
        "thickness",
        "present"
    )

    def __init__(
            self,
            data: Any,
            thickness: float = 2.0,
            colors: Union[str, np.ndarray, Iterable] = "w",
            alpha: float = 1.0,
            cmap: str = None,
            cmap_values: Union[np.ndarray, List] = None,
            z_position: float = None,
            collection_index: int = None,
            *args,
            **kwargs
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
            ex: ``scatter.data[:, 0] = 5```, ``scatter.data[xs > 5] = 3``

        **colors**: :class:`.ColorFeature`
            Manages the color buffer, allows regular and fancy indexing.
            ex: ``scatter.data[:, 1] = 0.5``, ``scatter.colors[xs > 5] = "cyan"``

        **present**: :class:`.PresentFeature`
            Control the presence of the Graphic in the scene, set to ``True`` or ``False``

        """

        self.data = PointsDataFeature(self, data, collection_index=collection_index)

        if cmap is not None:
            n_datapoints = self.data().shape[0]

            colors = parse_cmap_values(
                n_colors=n_datapoints,
                cmap_name=cmap,
                cmap_values=cmap_values
            )

        self.colors = ColorFeature(
            self,
            colors,
            n_colors=self.data().shape[0],
            alpha=alpha,
            collection_index=collection_index
        )

        self.cmap = CmapFeature(
            self,
            self.colors(),
            cmap_name=cmap,
            cmap_values=cmap_values
        )

        super(LineGraphic, self).__init__(*args, **kwargs)

        if thickness < 1.1:
            material = pygfx.LineThinMaterial
        else:
            material = pygfx.LineMaterial

        self.thickness = ThicknessFeature(self, thickness)

        world_object: pygfx.Line = pygfx.Line(
            # self.data.feature_data because data is a Buffer
            geometry=pygfx.Geometry(positions=self.data(), colors=self.colors()),
            material=material(thickness=self.thickness(), vertex_colors=True)
        )

        self._set_world_object(world_object)

        if z_position is not None:
            self.position_z = z_position

    def add_linear_selector(self, selection: int = None, padding: float = 50, **kwargs) -> LinearSelector:
        """
        Adds a linear selector.

        Parameters
        ----------
        selection: int
            initial position of the selector

        padding: float
            pad the length of the selector

        kwargs
            passed to :class:`.LinearSelector`

        Returns
        -------
        LinearSelector

        """

        bounds_init, limits, size, origin, axis, end_points = self._get_linear_selector_init_args(padding, **kwargs)

        if selection is None:
            selection = limits[0]

        if selection < limits[0] or selection > limits[1]:
            raise ValueError(f"the passed selection: {selection} is beyond the limits: {limits}")

        selector = LinearSelector(
            selection=selection,
            limits=limits,
            end_points=end_points,
            parent=self,
            **kwargs
        )

        self._plot_area.add_graphic(selector, center=False)
        selector.position_z = self.position_z + 1

        return weakref.proxy(selector)

    def add_linear_region_selector(self, padding: float = 100.0, **kwargs) -> LinearRegionSelector:
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

        bounds_init, limits, size, origin, axis, end_points = self._get_linear_selector_init_args(padding, **kwargs)

        # create selector
        selector = LinearRegionSelector(
            bounds=bounds_init,
            limits=limits,
            size=size,
            origin=origin,
            parent=self,
            **kwargs
        )

        self._plot_area.add_graphic(selector, center=False)
        # so that it is below this graphic
        selector.position_z = self.position_z - 1

        # PlotArea manages this for garbage collection etc. just like all other Graphics
        # so we should only work with a proxy on the user-end
        return weakref.proxy(selector)

    # TODO: this method is a bit of a mess, can refactor later
    def _get_linear_selector_init_args(self, padding: float, **kwargs):
        # computes initial bounds, limits, size and origin of linear selectors
        data = self.data()

        if "axis" in kwargs.keys():
            axis = kwargs["axis"]
        else:
            axis = "x"

        if axis == "x":
            offset = self.position_x
            # x limits
            limits = (data[0, 0] + offset, data[-1, 0] + offset)

            # height + padding
            size = np.ptp(data[:, 1]) + padding

            # initial position of the selector
            position_y = (data[:, 1].min() + data[:, 1].max()) / 2

            # need y offset too for this
            origin = (limits[0] - offset, position_y + self.position_y)

            # endpoints of the data range
            # used by linear selector but not linear region
            end_points = (self.data()[:, 1].min() - padding, self.data()[:, 1].max() + padding)
        else:
            offset = self.position_y
            # y limits
            limits = (data[0, 1] + offset, data[-1, 1] + offset)

            # width + padding
            size = np.ptp(data[:, 0]) + padding

            # initial position of the selector
            position_x = (data[:, 0].min() + data[:, 0].max()) / 2

            # need x offset too for this
            origin = (position_x + self.position_x, limits[0] - offset)

            end_points = (self.data()[:, 0].min() - padding, self.data()[:, 0].max() + padding)

        # initial bounds are 20% of the limits range
        bounds_init = (limits[0], int(np.ptp(limits) * 0.2) + offset)

        return bounds_init, limits, size, origin, axis, end_points

    def _add_plot_area_hook(self, plot_area):
        self._plot_area = plot_area

    def _set_feature(self, feature: str, new_data: Any, indices: Any = None):
        if not hasattr(self, "_previous_data"):
            self._previous_data = dict()
        elif hasattr(self, "_previous_data"):
            self._reset_feature(feature)

        feature_instance = getattr(self, feature)
        if indices is not None:
            previous = feature_instance[indices].copy()
            feature_instance[indices] = new_data
        else:
            previous = feature_instance._data.copy()
            feature_instance._set(new_data)
        if feature in self._previous_data.keys():
            self._previous_data[feature].data = previous
            self._previous_data[feature].indices = indices
        else:
            self._previous_data[feature] = PreviouslyModifiedData(data=previous, indices=indices)

    def _reset_feature(self, feature: str):
        if feature not in self._previous_data.keys():
            return

        prev_ixs = self._previous_data[feature].indices
        feature_instance = getattr(self, feature)
        if prev_ixs is not None:
            feature_instance[prev_ixs] = self._previous_data[feature].data
        else:
            feature_instance._set(self._previous_data[feature].data)