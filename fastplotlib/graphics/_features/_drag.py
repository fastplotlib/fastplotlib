from typing import *

import numpy as np

from . import GraphicFeature, FeatureEvent


class DragFeature(GraphicFeature):
    """
    Manages mouse and keyboard drag events
    """
    def __init__(
            self,
            parent,
            multiplier: Tuple[float, float, float] = None,
            limits: Tuple[float, float, float] = None,
    ):
        super(DragFeature, self).__init__(parent, data=None)
        self._multiplier = None
        self._limits = None

        self.multiplier = multiplier
        self.limits = limits

    @property
    def multiplier(self) -> Tuple[float, float, float]:
        return self._multiplier

    @multiplier.setter
    def multiplier(self, value: Tuple[float, float, float]):
        if value is None:
            self._multiplier = (1, 1, 1)
        else:
            if not all(np.issubdtype(type(v), np.number) for v in value):
                raise TypeError(
                    "multiplier must be in the form [x_mult, y_mult, z_mult] where each "
                    "axis multiplier is numeric"
                )

    @property
    def limits(self) -> Tuple[float, float, float]:
        return self._limits

    @limits.setter
    def limits(self, limits: Tuple[float, float, float]):
        if limits is None:
            limits = (None, None, None)

        # make sure limits are numeric
        for l in limits:
            if l is None:
                continue
            if not np.issubdtype(type(l), np.number):
                raise TypeError(
                    "limits must be in the form [x_limit, y_limit, z_limit] where "
                    "each axis limit is either numeric or None"
                )

        _limits = [None, None, None]
        for i in range(3):
            if limits[i] is not None:
                _limits[i] = limits[i]

        limits = tuple(_limits)

        self._limits = limits

    def _set(self, delta: Tuple[float, float, float]):
        """

        Parameters
        ----------
        delta: (float, float, float)
            drag vector

        """
        delta = np.array(delta)

        for i in range(3):
            delta[i] *= self.multiplier[i]

        self._parent.position = self._parent.position + delta

    def _feature_changed(self, key, new_data: np.ndarray):
        if len(self._event_handlers) < 1:
            return

        last_pygfx_event = self._parent.last_pygfx_event

        pick_info = {
            "world_object": self._parent.world_object,
            "delta": new_data,
            "graphic": self._parent,
            "last_pygfx_event": last_pygfx_event
        }

        event_data = FeatureEvent(type="drag", pick_info=pick_info)

        self._call_event_handlers(event_data)

    def __repr__(self) -> str:
        return f"DragFeature for {self._parent}"
