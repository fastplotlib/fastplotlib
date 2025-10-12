from typing import Sequence

import numpy as np

from ._base import GraphicFeature, GraphicFeatureEvent, block_reentrance


class Name(GraphicFeature):
    event_info_spec = [
        {"dict key": "value", "type": "str", "description": "user provided name"},
    ]

    def __init__(self, value: str, property_name: str = "name"):
        """Graphic name"""

        self._value = value
        super().__init__(property_name=property_name)

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

        event = GraphicFeatureEvent(type=self._property_name, info={"value": value})
        self._call_event_handlers(event)


class Offset(GraphicFeature):
    event_info_spec = [
        {
            "dict key": "value",
            "type": "np.ndarray[float, float, float]",
            "description": "new offset (x, y, z)",
        },
    ]

    def __init__(self, value: np.ndarray | Sequence[float], property_name: str = "offset"):
        """Offset position of the graphic, [x, y, z]"""

        self._validate(value)
        # initialize zeros array
        self._value = np.zeros(3)

        # set values
        self._value[:] = value
        super().__init__(property_name=property_name)

    def _validate(self, value):
        if not len(value) == 3:
            raise ValueError("offset must be a list, tuple, or array of 3 float values")

    @property
    def value(self) -> np.ndarray:
        return self._value

    @block_reentrance
    def set_value(self, graphic, value: np.ndarray | Sequence[float]):
        self._validate(value)
        value = np.asarray(value)

        graphic.world_object.world.position = value

        # sometimes there are transforms so get the final position value like this
        value = graphic.world_object.world.position.copy()

        # set value of existing feature value array
        self._value[:] = value

        event = GraphicFeatureEvent(type=self._property_name, info={"value": value})
        self._call_event_handlers(event)


class Rotation(GraphicFeature):
    event_info_spec = [
        {
            "dict key": "value",
            "type": "np.ndarray[float, float, float, float]",
            "description": "new rotation quaternion",
        },
    ]

    def __init__(self, value: np.ndarray | Sequence[float], property_name: str = "rotation"):
        """Graphic rotation quaternion"""

        self._validate(value)
        # create zeros array
        self._value = np.zeros(4)

        self._value[:] = value
        super().__init__(property_name=property_name)

    def _validate(self, value):
        if not len(value) == 4:
            raise ValueError(
                "rotation quaternion must be a list, tuple, or array of 4 float values"
            )

    @property
    def value(self) -> np.ndarray:
        return self._value

    @block_reentrance
    def set_value(self, graphic, value: np.ndarray | Sequence[float]):
        self._validate(value)
        value = np.asarray(value)

        graphic.world_object.world.rotation = value

        # get the actual final quaternion value, pygfx adjusts to make sure || q ||_2 == 1
        # i.e. pygfx checks to make sure norm 1 and other transforms
        value = graphic.world_object.world.rotation.copy()

        # set value of existing feature value array
        self._value[:] = value

        event = GraphicFeatureEvent(type=self._property_name, info={"value": value})
        self._call_event_handlers(event)


class Alpha(GraphicFeature):
    """The alpha value (i.e. opacity) of a graphic."""

    event_info_spec = [
        {"dict key": "value", "type": "float", "description": "new alpha value"},
    ]

    def __init__(self, value: float, property_name: str = "alpha"):
        self._value = value
        super().__init__(property_name=property_name)

    @property
    def value(self) -> float:
        return self._value

    @block_reentrance
    def set_value(self, graphic, value: float):
        wo = graphic.world_object
        if wo.material is not None:
            wo.material.opacity = value

        if "Image" in graphic.__class__.__name__:
            # Image and ImageVolume use tiling and share one material
            graphic._material.alpha = value

        self._value = value

        event = GraphicFeatureEvent(type=self._property_name, info={"value": value})
        self._call_event_handlers(event)


class AlphaMode(GraphicFeature):
    """The alpha-mode value of a graphic (i.e. how alpha is handled by the renderer)."""

    event_info_spec = [
        {"dict key": "value", "type": "str", "description": "new alpha mode"},
    ]

    def __init__(self, value: str, property_name: str = "alpha_mode"):
        self._value = value
        super().__init__(property_name=property_name)

    @property
    def value(self) -> str:
        return self._value

    @block_reentrance
    def set_value(self, graphic, value: str):
        wo = graphic.world_object
        if wo.material is not None:
            wo.alpha_mode = value

        if "Image" in graphic.__class__.__name__:
            # Image and ImageVolume use tiling and share one material
            graphic._material.alpha_mode = value

        self._value = value

        event = GraphicFeatureEvent(type=self._property_name, info={"value": value})
        self._call_event_handlers(event)


class Visible(GraphicFeature):
    """Access or change the visibility."""

    event_info_spec = [
        {"dict key": "value", "type": "bool", "description": "new visibility bool"},
    ]

    def __init__(self, value: bool, property_name: str = "visible"):
        self._value = value
        super().__init__(property_name=property_name)

    @property
    def value(self) -> bool:
        return self._value

    @block_reentrance
    def set_value(self, graphic, value: bool):
        graphic.world_object.visible = value
        self._value = value

        event = GraphicFeatureEvent(type=self._property_name, info={"value": value})
        self._call_event_handlers(event)


class Deleted(GraphicFeature):
    """
    Used when a graphic is deleted, triggers events that can be useful to indicate this graphic has been deleted
    """

    event_info_spec = [
        {
            "dict key": "value",
            "type": "bool",
            "description": "True when graphic was deleted",
        },
    ]

    def __init__(self, value: bool, property_name: str = "deleted"):
        self._value = value
        super().__init__(property_name=property_name)

    @property
    def value(self) -> bool:
        return self._value

    @block_reentrance
    def set_value(self, graphic, value: bool):
        self._value = value
        event = GraphicFeatureEvent(type=self._property_name, info={"value": value})
        self._call_event_handlers(event)
