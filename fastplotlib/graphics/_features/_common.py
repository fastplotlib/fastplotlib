import numpy as np

from ._base import GraphicFeature, FeatureEvent, block_reentrance


class Name(GraphicFeature):
    """Graphic name"""

    def __init__(self, value: str):
        self._value = value
        super().__init__()

    @property
    def value(self) -> str:
        return self._value

    @block_reentrance
    def set_value(self, graphic, value: str):
        if not isinstance(value, str):
            raise TypeError("`Graphic` name must be of type <str>")

        if graphic._plot_area is not None:
            graphic._plot_area._check_graphic_name_exists(value)

        self._value = value

        event = FeatureEvent(type="name", info={"value": value})
        self._call_event_handlers(event)


class Offset(GraphicFeature):
    """Offset position of the graphic, [x, y, z]"""

    def __init__(self, value: np.ndarray | list | tuple):
        self._validate(value)
        self._value = np.array(value)
        self._value.flags.writeable = False
        super().__init__()

    def _validate(self, value):
        if not len(value) == 3:
            raise ValueError("offset must be a list, tuple, or array of 3 float values")

    @property
    def value(self) -> np.ndarray:
        return self._value

    @block_reentrance
    def set_value(self, graphic, value: np.ndarray | list | tuple):
        self._validate(value)

        graphic.world_object.world.position = value
        self._value = graphic.world_object.world.position.copy()
        self._value.flags.writeable = False

        event = FeatureEvent(type="offset", info={"value": value})
        self._call_event_handlers(event)


class Rotation(GraphicFeature):
    """Graphic rotation quaternion"""

    def __init__(self, value: np.ndarray | list | tuple):
        self._validate(value)
        self._value = np.array(value)
        self._value.flags.writeable = False
        super().__init__()

    def _validate(self, value):
        if not len(value) == 4:
            raise ValueError(
                "rotation quaternion must be a list, tuple, or array of 4 float values"
            )

    @property
    def value(self) -> np.ndarray:
        return self._value

    @block_reentrance
    def set_value(self, graphic, value: np.ndarray | list | tuple):
        self._validate(value)

        graphic.world_object.world.rotation = value
        self._value = graphic.world_object.world.rotation.copy()
        self._value.flags.writeable = False

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

    @block_reentrance
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

    @block_reentrance
    def set_value(self, graphic, value: bool):
        self._value = value
        event = FeatureEvent(type="deleted", info={"value": value})
        self._call_event_handlers(event)
