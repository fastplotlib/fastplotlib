from typing import Sequence

import numpy as np

from ...utils import mesh_masks
from ._base import GraphicFeature, FeatureEvent


class LinearSelectionFeature(GraphicFeature):
    # A bit much to have a class for this but this allows it to integrate with the fastplotlib callback system
    """
    Manages the linear selection and callbacks
    """

    def __init__(self, axis: str, value: float, limits: tuple[float, float]):
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

    def set_value(self, selector, value: float):
        if not (self._limits[0] <= value <= self._limits[1]):
            return

        offset = list(selector.offset)

        if self._axis == "x":
            offset[0] = value
        else:
            offset[1] = value

        selector.offset = offset

        self._value = value
        event = FeatureEvent("selection", {"index": selector.get_selected_index()})
        self._call_event_handlers(event)


class LinearRegionSelectionFeature(GraphicFeature):
    """
    Feature for a linearly bounding region
    """

    def __init__(
        self, value: tuple[int, int], axis: str, limits: tuple[float, float]
    ):
        super().__init__()

        self._axis = axis
        self._limits = limits
        self._value = tuple(int(v) for v in value)

    @property
    def value(self) -> np.ndarray[float]:
        """
        (min, max) of the selection, in data space
        """
        return self._value

    @property
    def axis(self) -> str:
        """one of "x" | "y" """
        return self._axis

    def set_value(self, selector, value: Sequence[float]):
        """
        Set start, stop range of selector

        Parameters
        ----------
        selector: LinearRegionSelector

        value: (float, float)
             (min, max) values in data space

        """
        if not len(value) == 2:
            raise TypeError(
                "selection must be a array, tuple, list, or sequence in the form of `(min, max)`, "
                "where `min` and `max` are numeric values."
            )

        # convert to array, clip values if they are beyond the limits
        value = np.asarray(value, dtype=np.float32).clip(*self._limits)

        # make sure `selector width >= 2`, left edge must not move past right edge!
        # or bottom edge must not move past top edge!
        if not (value[1] - value[0]) >= 0:
            return

        if self.axis == "x":
            # change left x position of the fill mesh
            selector.fill.geometry.positions.data[mesh_masks.x_left] = value[0]

            # change right x position of the fill mesh
            selector.fill.geometry.positions.data[mesh_masks.x_right] = value[1]

            # change x position of the left edge line
            selector.edges[0].geometry.positions.data[:, 0] = value[0]

            # change x position of the right edge line
            selector.edges[1].geometry.positions.data[:, 0] = value[1]

        elif self.axis == "y":
            # change bottom y position of the fill mesh
            selector.fill.geometry.positions.data[mesh_masks.y_bottom] = value[0]

            # change top position of the fill mesh
            selector.fill.geometry.positions.data[mesh_masks.y_top] = value[1]

            # change y position of the bottom edge line
            selector.edges[0].geometry.positions.data[:, 1] = value[0]

            # change y position of the top edge line
            selector.edges[1].geometry.positions.data[:, 1] = value[1]

        self._value = value

        # send changes to GPU
        selector.fill.geometry.positions.update_range()

        selector.edges[0].geometry.positions.update_range()
        selector.edges[1].geometry.positions.update_range()

        # send event
        if len(self._event_handlers) > 0:
            return

        # event = FeatureEvent("selection", {"indices": selector.get_selected_indices()})
        # self._call_event_handlers(event)
        # TODO: user's selector event handlers can call event.graphic.get_selected_indices() to get the data index,
        #  and event.graphic.get_selected_data() to get the data under the selection
        #  this is probably a good idea so that the data isn't sliced until it's actually necessary
