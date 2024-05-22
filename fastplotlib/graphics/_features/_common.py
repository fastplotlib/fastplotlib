from ._base import GraphicFeature, FeatureEvent


class Name(GraphicFeature):
    """Graphic name"""
    def __init__(self, value: str):
        self._value = value
        super().__init__()

    @property
    def value(self) -> str:
        return self._value

    def set_value(self, graphic, value: bool):
        if not isinstance(value, str):
            raise TypeError("`Graphic` name must be of type <str>")

        if graphic._plot_area is not None:
            graphic._plot_area._check_graphic_name_exists(value)

        self._value = value

        event = FeatureEvent(type="name", info={"value": value})
        self._call_event_handlers(event)


class Offset(GraphicFeature):
    """Offset position of the graphic, [x, y, z]"""
    def __init__(self, value: tuple[float, float, float]):
        self._value = value
        super().__init__()

    @property
    def value(self) -> tuple[float, float, float]:
        return self._value

    def set_value(self, graphic, value: tuple[float, float, float]):
        if not len(value) == 3:
            raise ValueError("offset must be a list, tuple, or array of 3 float values")

        graphic.position = value
        self._value = value

        event = FeatureEvent(type="offset", info={"value": value})
        self._call_event_handlers(event)


class Rotation(GraphicFeature):
    """Graphic rotation quaternion"""
    def __init__(self, value: tuple[float, float, float, float]):
        self._value = value
        super().__init__()

    @property
    def value(self) -> tuple[float, float, float, float]:
        return self._value

    def set_value(self, graphic, value: tuple[float, float, float, float]):
        if not len(value) == 4:
            raise ValueError("rotation must be a list, tuple, or array of 4 float values"
                             "representing a quaternion")

        graphic.rotation = value
        self._value = value

        event = FeatureEvent(type="rotation", info={"value": value})
        self._call_event_handlers(event)


class Visible(GraphicFeature):
    """Access or change the visibility."""
    def __init__(self, value: bool):
        self._value = value
        super().__init__()

    @property
    def value(self) -> bool:
        return self._value

    def set_value(self, graphic, value: bool):
        graphic.world_object.visible = value
        self._value = value

        event = FeatureEvent(type="visible", info={"value": value})
        self._call_event_handlers(event)


class Deleted(GraphicFeature):
    """
    Used when a graphic is deleted, triggers events that can be useful to indicate this graphic has been deleted
    """
    def __init__(self, value: bool):
        self._value = value
        super().__init__()

    @property
    def value(self) -> bool:
        return self._value

    def set_value(self, graphic, value: bool):
        self._value = value
        event = FeatureEvent(type="deleted", info={"value": value})
        self._call_event_handlers(event)
