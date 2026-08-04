from ._base import (
    GraphicFeature,
    GraphicFeatureEvent,
    block_reentrance,
)


# matplotlib-style dash pattern presets, expressed in units relative to the line thickness
DASH_PATTERNS: dict[str, tuple] = {
    "-": (),
    "solid": (),
    "--": (5, 5),
    "dashed": (5, 5),
    "-.": (5, 2, 1, 2),
    "dashdot": (5, 2, 1, 2),
    ":": (0, 2),
    "dotted": (0, 2),
}


def parse_dash_pattern(value: str | tuple | list) -> tuple:
    """
    Parse a ``dash_pattern`` into a pygfx dash tuple.

    ``value`` can be a matplotlib-style string, one of
    ``"-", "--", "-.", ":"`` or ``"solid", "dashed", "dashdot", "dotted"``, or a
    sequence of floats describing the length of strokes and gaps.
    """
    if isinstance(value, str):
        if value not in DASH_PATTERNS:
            raise ValueError(
                f"`dash_pattern` string must be one of {sorted(DASH_PATTERNS.keys())}, "
                f"you have passed: {value!r}"
            )
        return DASH_PATTERNS[value]

    return tuple(value)


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


class DashPattern(GraphicFeature):
    event_info_spec = [
        {
            "dict key": "value",
            "type": "str | tuple",
            "description": "new dash pattern",
        },
    ]

    def __init__(self, value: str | tuple | list = (), property_name: str = "dash_pattern"):
        # parse to validate, but store the user's original value so it stays readable
        parse_dash_pattern(value)
        self._value = value
        super().__init__(property_name=property_name)

    @property
    def value(self) -> str | tuple:
        return self._value

    @block_reentrance
    def set_value(self, graphic, value: str | tuple | list):
        graphic.world_object.material.dash_pattern = parse_dash_pattern(value)
        self._value = value

        event = GraphicFeatureEvent(type=self._property_name, info={"value": value})
        self._call_event_handlers(event)
