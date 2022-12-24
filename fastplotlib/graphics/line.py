from typing import *
import numpy as np
import pygfx

from ._base import Graphic, Interaction, PreviouslyModifiedData


class LineGraphic(Graphic, Interaction):
    def __init__(
            self,
            data: Any,
            z_position: float = 0.0,
            size: float = 2.0,
            colors: Union[str, np.ndarray, Iterable] = "w",
            cmap: str = None,
            *args,
            **kwargs
    ):
        """
        Create a line Graphic, 2d or 3d
        Parameters
        ----------
        data: array-like
            Line data to plot, 2D must be of shape [n_points, 2], 3D must be of shape [n_points, 3]
        z_position: float, optional
            z-axis position for placing the graphic
        size: float, optional
            thickness of the line
        colors: str, array, or iterable
            specify colors as a single human readable string, a single RGBA array,
            or an iterable of strings or RGBA arrays
        cmap: str, optional
            apply a colormap to the line instead of assigning colors manually
        args
            passed to Graphic
        kwargs
            passed to Graphic
        """

        super(LineGraphic, self).__init__(data, colors=colors, cmap=cmap, *args, **kwargs)

        if size < 1.1:
            material = pygfx.LineThinMaterial
        else:
            material = pygfx.LineMaterial

        # self.data = np.ascontiguousarray(self.data)

        self._world_object: pygfx.Line = pygfx.Line(
            # self.data.feature_data because data is a Buffer
            geometry=pygfx.Geometry(positions=self.data.feature_data, colors=self.colors.feature_data),
            material=material(thickness=size, vertex_colors=True)
        )

        self.world_object.position.z = z_position

    def _set_feature(self, feature: str, new_data: Any, indices: Any = None):
        if not hasattr(self, "_previous_data"):
            self._previous_data = {}
        elif hasattr(self, "_previous_data"):
            self._reset_feature(feature)
        if feature in self._feature_events:
            feature_instance = getattr(self, feature)
            if indices is not None:
                previous = feature_instance[indices].copy()
                feature_instance[indices] = new_data
            else:
                previous = feature_instance[:].copy()
                feature_instance[:] = new_data
            if feature in self._previous_data.keys():
                self._previous_data[feature].previous_data = previous
                self._previous_data[feature].previous_indices = indices
            else:
                self._previous_data[feature] = PreviouslyModifiedData(previous_data=previous, previous_indices=indices)
        else:
            raise ValueError("name arg is not a valid feature")


    def _reset_feature(self, feature: str):
        if feature not in self._previous_data.keys():
            raise ValueError("no previous data registered for this feature")
        else:
            feature_instance = getattr(self, feature)
            if self._previous_data[feature].previous_indices is not None:
                feature_instance[self._previous_data[feature].previous_indices] = self._previous_data[feature].previous_data
            else:
                feature_instance[:] = self._previous_data[feature].previous_data

