import numpy as np

import pygfx

from ._base import GraphicFeature, GraphicFeatureEvent, block_reentrance


class TextData(GraphicFeature):
    event_info_spec = [
        {
            "dict key": "value",
            "type": "str",
            "description": "new text data",
        },
    ]

    def __init__(self, value: str):
        self._value = value
        super().__init__(property_name="text")

    @property
    def value(self) -> str:
        return self._value

    @block_reentrance
    def set_value(self, graphic, value: str):
        graphic.world_object.set_text(value)
        self._value = value

        event = GraphicFeatureEvent(type=self._property_name, info={"value": value})
        self._call_event_handlers(event)


class FontSize(GraphicFeature):
    event_info_spec = [
        {
            "dict key": "value",
            "type": "float | int",
            "description": "new font size",
        },
    ]

    def __init__(self, value: float | int):
        self._value = value
        super().__init__(property_name="font_size")

    @property
    def value(self) -> float | int:
        return self._value

    @block_reentrance
    def set_value(self, graphic, value: float | int):
        graphic.world_object.font_size = value
        self._value = graphic.world_object.font_size

        event = GraphicFeatureEvent(type=self._property_name, info={"value": value})
        self._call_event_handlers(event)


class TextFaceColor(GraphicFeature):
    event_info_spec = [
        {
            "dict key": "value",
            "type": "str | np.ndarray",
            "description": "new text color",
        },
    ]

    def __init__(self, value: str | np.ndarray | list[float] | tuple[float]):
        self._value = pygfx.Color(value)
        super().__init__(property_name="face_color")

    @property
    def value(self) -> pygfx.Color:
        return self._value

    @block_reentrance
    def set_value(self, graphic, value: str | np.ndarray | list[float] | tuple[float]):
        value = pygfx.Color(value)
        graphic.world_object.material.color = value
        self._value = graphic.world_object.material.color

        event = GraphicFeatureEvent(type=self._property_name, info={"value": value})
        self._call_event_handlers(event)


class TextOutlineColor(GraphicFeature):
    event_info_spec = [
        {
            "dict key": "value",
            "type": "str | np.ndarray",
            "description": "new outline color",
        },
    ]

    def __init__(self, value: str | np.ndarray | list[float] | tuple[float]):
        self._value = pygfx.Color(value)
        super().__init__(property_name="outline_color")

    @property
    def value(self) -> pygfx.Color:
        return self._value

    @block_reentrance
    def set_value(self, graphic, value: str | np.ndarray | list[float] | tuple[float]):
        value = pygfx.Color(value)
        graphic.world_object.material.outline_color = value
        self._value = graphic.world_object.material.outline_color

        event = GraphicFeatureEvent(type=self._property_name, info={"value": value})
        self._call_event_handlers(event)


class TextOutlineThickness(GraphicFeature):
    event_info_spec = [
        {
            "dict key": "value",
            "type": "float",
            "description": "new text outline thickness",
        },
    ]

    def __init__(self, value: float):
        self._value = value
        super().__init__(property_name="outline_thickness")

    @property
    def value(self) -> float:
        return self._value

    @block_reentrance
    def set_value(self, graphic, value: float):
        graphic.world_object.material.outline_thickness = value
        self._value = graphic.world_object.material.outline_thickness

        event = GraphicFeatureEvent(type=self._property_name, info={"value": value})
        self._call_event_handlers(event)
