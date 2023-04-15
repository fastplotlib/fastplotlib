from typing import *
import numpy as np
import pygfx

from ._base import Graphic, Interaction, PreviouslyModifiedData
from .features import PointsDataFeature, ColorFeature, CmapFeature, ThicknessFeature
from .selectors import LinearSelector
from ..utils import make_colors


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
            specify colors as a single human readable string, a single RGBA array,
            or an iterable of strings or RGBA arrays

        cmap: str, optional
            apply a colormap to the line instead of assigning colors manually, this
            overrides any argument passed to "colors"

        alpha: float, optional, default 1.0
            alpha value for the colors

        z_position: float, optional
            z-axis position for placing the graphic

        args
            passed to Graphic

        kwargs
            passed to Graphic

        """

        self.data = PointsDataFeature(self, data, collection_index=collection_index)

        if cmap is not None:
            colors = make_colors(n_colors=self.data().shape[0], cmap=cmap, alpha=alpha)

        self.colors = ColorFeature(
            self,
            colors,
            n_colors=self.data().shape[0],
            alpha=alpha,
            collection_index=collection_index
        )

        self.cmap = CmapFeature(self, self.colors())

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
            self.world_object.position.z = z_position

        self.selectors: List[LinearSelector] = list()

    def add_linear_selector(self, padding: float = 100.0, **kwargs):
        """
        Add a ``LinearSelector``.

        Parameters
        ----------
        padding: float, default 100.0
            Extends the linear selector along the y-axis to make it easier to interact with.

        kwargs
            passed to ``LinearSelector``

        Returns
        -------
        LinearSelector
            linear selection graphic
        """
        data = self.data()
        # x limits
        x_limits = (data[0, 0], data[-1, 0])

        # initial bounds are 20% of the limits range
        bounds_init = (x_limits[0], int(np.ptp(x_limits) * 0.2))

        # width of the y-vals + padding
        height = np.ptp(data[:, 1]) + padding

        # initial position of the selector
        position_y = (data[:, 1].min() + data[:, 1].max()) / 2
        position = (x_limits[0], position_y)

        # create selector
        selector = LinearSelector(
            bounds=bounds_init,
            limits=x_limits,
            height=height,
            position=position,
            parent=self,
            **kwargs
        )

        self._plot_area.add_graphic(selector, center=False)
        # so that it is below this graphic
        selector.position.set_z(self.position.z - 1)
        
        self.selectors.append(selector)

        return selector

    def remove_selector(self, selector: LinearSelector):
        self.selectors.remove(selector)
        self._plot_area.delete_graphic(selector)

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