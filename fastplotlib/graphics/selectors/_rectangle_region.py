from typing import *
import numpy as np

import pygfx
from pygfx.linalg import Vector3

from .._base import Graphic, GraphicCollection
from ..features._base import GraphicFeature, FeatureEvent
from ._base_selector import BaseSelector

from ._mesh_positions import x_right, x_left, y_top, y_bottom


class RectangleRegionSelector(Graphic, BaseSelector):
    feature_events = (
        "bounds"
    )

    def __init__(
            self,
            bounds: Tuple[int, int, int, int],
            limits: Tuple[int, int],
            size: int,
            origin: Tuple[int, int],
            axis: str = "x",
            parent: Graphic = None,
            resizable: bool = True,
            fill_color=(0, 0, 0.35),
            edge_color=(0.8, 0.8, 0),
            arrow_keys_modifier: str = "Shift",
            name: str = None
    ):
        """
        Create a LinearRegionSelector graphic which can be moved only along either the x-axis or y-axis.
        Allows sub-selecting data from a ``Graphic`` or from multiple Graphics.

        bounds[0], limits[0], and position[0] must be identical

        Parameters
        ----------
        bounds: (int, int, int, int)
            the initial bounds of the rectangle, ``(x_min, x_max, y_min, y_max)``

        limits: (int, int, int, int)
            limits of the selector, ``(x_min, x_max, y_min, y_max)``

        origin: (int, int)
            initial position of the selector

        axis: str, default ``None``
            Restrict the selector to the "x" or "y" axis.
            If the selector is restricted to an axis you cannot change the bounds along the other axis. For example,
            if you set ``axis="x"``, then the ``y_min``, ``y_max`` values of the bounds will stay constant.

        parent: Graphic, default ``None``
            associate this selector with a parent Graphic

        resizable: bool
            if ``True``, the edges can be dragged to resize the selection

        fill_color: str, array, or tuple
            fill color for the selector, passed to pygfx.Color

        edge_color: str, array, or tuple
            edge color for the selector, passed to pygfx.Color

        name: str
            name for this selector graphic
        """