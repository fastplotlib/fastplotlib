from ._base import GraphicFeature, FeatureEvent


class ThicknessFeature(GraphicFeature):
    """
    Used by Line graphics for line material thickness.
    """

    def __init__(self, thickness: float):
        self._value = thickness
        super().__init__()

    @property
    def value(self) -> float:
        return self._value

    def set_value(self, parent, value: float):
        parent.world_object.material.thickness = value

        event = FeatureEvent("thickness", {"value": value})
        self._call_event_handlers(event)
