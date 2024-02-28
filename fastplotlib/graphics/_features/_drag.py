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
            multiplier: np.ndarray = None,
            clamp: np.ndarray = None,
    ):
        super(DragFeature, self).__init__(parent, data=None)
        self._multiplier = None
        self._clamp = None

        self.multiplier = multiplier
        self.clamp = clamp

    @property
    def multiplier(self) -> np.ndarray:
        return self._multiplier

    @multiplier.setter
    def multiplier(self, value: np.ndarray):
        if value is None:
            self._multiplier = np.array([1., 1., 1.])

        self._multiplier = np.array(value)

    @property
    def clamp(self) -> np.ndarray:
        """
        Returns
        -------
        np.ndarray
            [[xmin, ymin, zmin], [xmax, ymax, zmax]]

        """
        return self._clamp

    @clamp.setter
    def clamp(self, clamp: np.ndarray):
        if clamp is None:
            clamp = np.zeros(shape=(2, 3), dtype=np.float32)
            clamp[:] = np.inf

        elif isinstance(clamp, np.ndarray):
            if clamp.shape not in [(2, 2), (2, 3)]:
                raise ValueError(
                    "clamp must be array of shape (2, 2) or (2, 3), see the docstring"
                )
            if clamp.shape == (2, 2):
                # add z with inf clamp
                clamp = np.column_stack([clamp, np.array([[np.inf], [np.inf]])])
        else:
            raise ValueError(
                "clamp must be array of shape (2, 2) or (2, 3), see the docstring"
            )

        self._clamp = clamp

    def _set(self, delta: np.ndarray):
        """

        Parameters
        ----------
        delta: (float, float, float)
            drag vector

        """
        delta = np.array(delta) * self.multiplier

        # add delta vector and clamp
        self._parent.position = (self._parent.position + delta).clip(self.clamp[0], self.clamp[1]).astype(np.float32)

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
