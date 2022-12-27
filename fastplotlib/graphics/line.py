from typing import *
import numpy as np
import pygfx

from ._base import Graphic
from .features import PointsDataFeature, ColorFeature, CmapFeature
from ..utils import get_colors


class LineGraphic(Graphic):
    def __init__(
            self,
            data: Any,
            size: float = 2.0,
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

        size: float, optional, default 2.0
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
            colors = get_colors(n_colors=self.data.feature_data.shape[0], cmap=cmap, alpha=alpha)

        self.colors = ColorFeature(
            self,
            colors,
            n_colors=self.data.feature_data.shape[0],
            alpha=alpha,
            collection_index=collection_index
        )

        self.cmap = CmapFeature(self, self.colors.feature_data)

        super(LineGraphic, self).__init__(*args, **kwargs)

        if size < 1.1:
            material = pygfx.LineThinMaterial
        else:
            material = pygfx.LineMaterial

        self._world_object: pygfx.Line = pygfx.Line(
            # self.data.feature_data because data is a Buffer
            geometry=pygfx.Geometry(positions=self.data.feature_data, colors=self.colors.feature_data),
            material=material(thickness=size, vertex_colors=True)
        )

        if z_position is not None:
            self.world_object.position.z = z_position
