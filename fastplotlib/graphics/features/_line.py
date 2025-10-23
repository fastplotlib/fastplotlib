from ._base import (
    GraphicFeature,
    GraphicFeatureEvent,
    block_reentrance,
)


class Thickness(GraphicFeature):
    event_info_spec = [
        {"dict key": "value", "type": "float", "description": "new thickness value"},
    ]

    def __init__(self, value: float, property_name: str = "thickness"):
        self._value = value
        super().__init__(property_name=property_name)

    @property
    def value(self) -> float:
        return self._value

    @block_reentrance
    def set_value(self, graphic, value: float):
        value = float(value)
        graphic.world_object.material.thickness = value
        self._value = value

        event = GraphicFeatureEvent(type=self._property_name, info={"value": value})
        self._call_event_handlers(event)
