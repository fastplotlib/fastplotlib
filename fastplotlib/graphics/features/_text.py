import numpy as np

import pygfx

from ._base import GraphicFeature, FeatureEvent, block_reentrance


class TextData(GraphicFeature):
    def __init__(self, value: str):
        self._value = value
        super().__init__()

    @property
    def value(self) -> str:
        return self._value

    @block_reentrance
    def set_value(self, graphic, value: str):
        graphic.world_object.set_text(value)
        self._value = value

        event = FeatureEvent(type="text", info={"value": value})
        self._call_event_handlers(event)


class FontSize(GraphicFeature):
    def __init__(self, value: float | int):
        self._value = value
        super().__init__()

    @property
    def value(self) -> float | int:
        return self._value

    @block_reentrance
    def set_value(self, graphic, value: float | int):
        graphic.world_object.font_size = value
        self._value = graphic.world_object.font_size

        event = FeatureEvent(type="font_size", info={"value": value})
        self._call_event_handlers(event)


class TextFaceColor(GraphicFeature):
    def __init__(self, value: str | np.ndarray | list[float] | tuple[float]):
        self._value = pygfx.Color(value)
        super().__init__()

    @property
    def value(self) -> pygfx.Color:
        return self._value

    @block_reentrance
    def set_value(self, graphic, value: str | np.ndarray | list[float] | tuple[float]):
        value = pygfx.Color(value)
        graphic.world_object.material.color = value
        self._value = graphic.world_object.material.color

        event = FeatureEvent(type="face_color", info={"value": value})
        self._call_event_handlers(event)


class TextOutlineColor(GraphicFeature):
    def __init__(self, value: str | np.ndarray | list[float] | tuple[float]):
        self._value = pygfx.Color(value)
        super().__init__()

    @property
    def value(self) -> pygfx.Color:
        return self._value

    @block_reentrance
    def set_value(self, graphic, value: str | np.ndarray | list[float] | tuple[float]):
        value = pygfx.Color(value)
        graphic.world_object.material.outline_color = value
        self._value = graphic.world_object.material.outline_color

        event = FeatureEvent(type="outline_color", info={"value": value})
        self._call_event_handlers(event)


class TextOutlineThickness(GraphicFeature):
    def __init__(self, value: float):
        self._value = value
        super().__init__()

    @property
    def value(self) -> float:
        return self._value

    @block_reentrance
    def set_value(self, graphic, value: float):
        graphic.world_object.material.outline_thickness = value
        self._value = graphic.world_object.material.outline_thickness

        event = FeatureEvent(type="outline_thickness", info={"value": value})
        self._call_event_handlers(event)
