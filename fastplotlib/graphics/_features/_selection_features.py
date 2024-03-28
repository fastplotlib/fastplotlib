from typing import Tuple, Union, Any

import numpy as np

from ...utils import mesh_masks
from ._base import GraphicFeature, FeatureEvent


class LinearSelectionFeature(GraphicFeature):
    # A bit much to have a class for this but this allows it to integrate with the fastplotlib callback system
    """
    Manages the linear selection and callbacks

    **event pick info**

     ===================  ===============================  =================================================================================================
      key                  type                             selection
     ===================  ===============================  =================================================================================================
      "selected_index"     ``int``                          the graphic data index that corresponds to the selector position
      "world_object"       ``pygfx.WorldObject``            pygfx WorldObject
      "new_data"           ``numpy.ndarray`` or ``None``    the new selector position in world coordinates, not necessarily the same as "selected_index"
      "graphic"            ``Graphic``                      the selector graphic
      "delta"              ``numpy.ndarray``                the delta vector of the graphic in NDC
      "pygfx_event"        ``pygfx.Event``                  pygfx Event
     ===================  ===============================  =================================================================================================

    """

    def __init__(self, parent, axis: str, value: float, limits: Tuple[int, int]):
        super().__init__(parent, data=value)

        self._axis = axis
        self._limits = limits

    def _set(self, value: float):
        if not (self._limits[0] <= value <= self._limits[1]):
            return

        if self._axis == "x":
            self._parent.position_x = value
        else:
            self._parent.position_y = value

        self._data = value
        self._feature_changed(key=None, new_data=value)

    def _feature_changed(self, key: Union[int, slice, Tuple[slice]], new_data: Any):
        if len(self._event_handlers) < 1:
            return

        if self._parent.parent is not None:
            g_ix = self._parent.get_selected_index()
        else:
            g_ix = None

        # get pygfx event and reset it
        pygfx_ev = self._parent._pygfx_event
        self._parent._pygfx_event = None

        pick_info = {
            "world_object": self._parent.world_object,
            "new_data": new_data,
            "selected_index": g_ix,
            "graphic": self._parent,
            "pygfx_event": pygfx_ev,
            "delta": self._parent.delta,
        }

        event_data = FeatureEvent(type="selection", pick_info=pick_info)

        self._call_event_handlers(event_data)

    def __repr__(self) -> str:
        s = f"LinearSelectionFeature for {self._parent}"
        return s


class LinearRegionSelectionFeature(GraphicFeature):
    """
    Feature for a linearly bounding region

    **event pick info**

    ===================== =============================== =======================================================================================
      key                  type                            description
    ===================== =============================== =======================================================================================
      "selected_indices"   ``numpy.ndarray`` or ``None``   selected graphic data indices
      "world_object"       ``pygfx.WorldObject``           pygfx World Object
      "new_data"           ``(float, float)``              current bounds in world coordinates, NOT necessarily the same as "selected_indices".
      "graphic"            ``Graphic``                     the selection graphic
      "delta"              ``numpy.ndarray``               the delta vector of the graphic in NDC
      "pygfx_event"        ``pygfx.Event``                 pygfx Event
      "selected_data"      ``numpy.ndarray`` or ``None``   selected graphic data
      "move_info"          ``MoveInfo``                    last position and event source (pygfx.Mesh or pygfx.Line)
    ===================== =============================== =======================================================================================

    """

    def __init__(
        self, parent, selection: Tuple[int, int], axis: str, limits: Tuple[int, int]
    ):
        super().__init__(parent, data=selection)

        self._axis = axis
        self._limits = limits

        self._set(selection)

    @property
    def axis(self) -> str:
        """one of "x" | "y" """
        return self._axis

    def _set(self, value: Tuple[float, float]):
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
            self._parent.fill.geometry.positions.data[mesh_masks.x_left] = value[0]

            # change right x position of the fill mesh
            self._parent.fill.geometry.positions.data[mesh_masks.x_right] = value[1]

            # change x position of the left edge line
            self._parent.edges[0].geometry.positions.data[:, 0] = value[0]

            # change x position of the right edge line
            self._parent.edges[1].geometry.positions.data[:, 0] = value[1]

        elif self.axis == "y":
            # change bottom y position of the fill mesh
            self._parent.fill.geometry.positions.data[mesh_masks.y_bottom] = value[0]

            # change top position of the fill mesh
            self._parent.fill.geometry.positions.data[mesh_masks.y_top] = value[1]

            # change y position of the bottom edge line
            self._parent.edges[0].geometry.positions.data[:, 1] = value[0]

            # change y position of the top edge line
            self._parent.edges[1].geometry.positions.data[:, 1] = value[1]

        self._data = value  # (value[0], value[1])

        # send changes to GPU
        self._parent.fill.geometry.positions.update_range()

        self._parent.edges[0].geometry.positions.update_range()
        self._parent.edges[1].geometry.positions.update_range()

        # calls any events
        self._feature_changed(key=None, new_data=value)

    def _feature_changed(self, key: Union[int, slice, Tuple[slice]], new_data: Any):
        if len(self._event_handlers) < 1:
            return

        if self._parent.parent is not None:
            selected_ixs = self._parent.get_selected_indices()
            selected_data = self._parent.get_selected_data()
        else:
            selected_ixs = None
            selected_data = None

        # get pygfx event and reset it
        pygfx_ev = self._parent._pygfx_event
        self._parent._pygfx_event = None

        pick_info = {
            "world_object": self._parent.world_object,
            "new_data": new_data,
            "selected_indices": selected_ixs,
            "selected_data": selected_data,
            "graphic": self._parent,
            "delta": self._parent.delta,
            "pygfx_event": pygfx_ev,
            "move_info": self._parent._move_info,
        }

        event_data = FeatureEvent(type="selection", pick_info=pick_info)

        self._call_event_handlers(event_data)

    def __repr__(self) -> str:
        s = f"LinearRegionSelectionFeature for {self._parent}"
        return s
