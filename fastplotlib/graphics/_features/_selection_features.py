from typing import Tuple, Union, Any

import numpy as np

from ...utils import mesh_masks
from ._base import GraphicFeature, FeatureEvent


class LinearSelectionFeature(GraphicFeature):
    # A bit much to have a class for this but this allows it to integrate with the fastplotlib callback system
    """
    Manages the linear selection and callbacks
    """

    def __init__(self, axis: str, value: float, limits: Tuple[float, float]):
        """

        Parameters
        ----------
        axis: "x" | "y"
            axis the selector is restricted to

        value: float
            position of the slider in world space, NOT data space
        limits: (float, float)
            min, max limits of the selector

        """

        super().__init__()

        self._axis = axis
        self._limits = limits
        self._value = value

    @property
    def value(self) -> float:
        """
        selection in world space, NOT data space
        """
        # TODO: Not sure if we should make this public since it's in world space, not data space
        #  need to decide if we give a value based on the selector's parent graphic, if there is one
        return self._value

    def set_value(self, graphic, value: float):
        if not (self._limits[0] <= value <= self._limits[1]):
            return

        offset = list(graphic.offset)

        if self._axis == "x":
            offset[0] = value
        else:
            offset[1] = value

        graphic.offset = offset

        self._value = value
        event = FeatureEvent("selection", {"index": graphic.get_selected_index()})
        self._call_event_handlers(event)


class LinearRegionSelectionFeature(GraphicFeature):
    """
    Feature for a linearly bounding region
    """

    def __init__(
        self, value: Tuple[int, int], axis: str, limits: Tuple[int, int]
    ):
        super().__init__()

        self._axis = axis
        self._limits = limits
        self._value = value

    @property
    def value(self) -> float:
        """
        selection in world space, NOT data space
        """
        return self._value

    @property
    def axis(self) -> str:
        """one of "x" | "y" """
        return self._axis

    def set_value(self, graphic, value: Tuple[float, float]):
        # sets new bounds
        if not isinstance(value, tuple):
            raise TypeError(
                "Bounds must be a tuple in the form of `(min_bound, max_bound)`, "
                "where `min_bound` and `max_bound` are numeric values."
            )

        # make sure bounds not exceeded
        for v in value:
            if not (self._limits[0] <= v <= self._limits[1]):
                return

        # make sure `selector width >= 2`, left edge must not move past right edge!
        # or bottom edge must not move past top edge!
        # has to be at least 2 otherwise can't join datapoints for lines
        if not (value[1] - value[0]) >= 2:
            return

        if self.axis == "x":
            # change left x position of the fill mesh
            graphic.fill.geometry.positions.data[mesh_masks.x_left] = value[0]

            # change right x position of the fill mesh
            graphic.fill.geometry.positions.data[mesh_masks.x_right] = value[1]

            # change x position of the left edge line
            graphic.edges[0].geometry.positions.data[:, 0] = value[0]

            # change x position of the right edge line
            graphic.edges[1].geometry.positions.data[:, 0] = value[1]

        elif self.axis == "y":
            # change bottom y position of the fill mesh
            graphic.fill.geometry.positions.data[mesh_masks.y_bottom] = value[0]

            # change top position of the fill mesh
            graphic.fill.geometry.positions.data[mesh_masks.y_top] = value[1]

            # change y position of the bottom edge line
            graphic.edges[0].geometry.positions.data[:, 1] = value[0]

            # change y position of the top edge line
            graphic.edges[1].geometry.positions.data[:, 1] = value[1]

        self._value = value  # (value[0], value[1])

        # send changes to GPU
        graphic.fill.geometry.positions.update_range()

        graphic.edges[0].geometry.positions.update_range()
        graphic.edges[1].geometry.positions.update_range()

        # send event
        event = FeatureEvent("selection", {"value": value})
        self._call_event_handlers(event)
        # TODO: user's selector event handlers can call event.graphic.get_selected_indices() to get the data index,
        #  and event.graphic.get_selected_data() to get the data under the selection
        #  this is probably a good idea so that the data isn't sliced until it's actually necessary
