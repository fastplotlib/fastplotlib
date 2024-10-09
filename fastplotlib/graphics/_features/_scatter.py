"""
features unique to ScatterGraphic
"""

import numpy as np
import pygfx

from ._base import (
    GraphicFeature,
    FeatureEvent,
)


class ScatterMarker(GraphicFeature):
    def __init__(self, value: str):
        self._value = value
        super().__init__()

    @property
    def value(self) -> str:
        return self._value

    def set_value(self, graphic, value: str):
        graphic.world_object.material.marker = value
        self._value = value

        event = FeatureEvent(type="marker", info={"value": value})
        self._call_event_handlers(event)


class ScatterEdgeColor(GraphicFeature):
    def __init__(
        self, value: str | np.ndarray | tuple | list | pygfx.Color, alpha: float = 1.0
    ):
        v = (*tuple(pygfx.Color(value))[:-1], alpha)  # apply alpha
        self._value = pygfx.Color(v)
        super().__init__()

    @property
    def value(self) -> pygfx.Color:
        return self._value

    def set_value(self, graphic, value: str | np.ndarray | tuple | list | pygfx.Color):
        value = pygfx.Color(value)
        graphic.world_object.material.edge_color = value
        self._value = value

        event = FeatureEvent(type="edge_color", info={"value": value})
        self._call_event_handlers(event)


class ScatterEdgeWidth(GraphicFeature):
    def __init__(self, value: float):
        self._value = float(value)
        super().__init__()

    @property
    def value(self) -> float:
        return self._value

    def set_value(self, graphic, value: float):
        graphic.world_object.material.edge_width = float(value)
        self._value = value

        event = FeatureEvent(type="edge_width", info={"value": value})
        self._call_event_handlers(event)