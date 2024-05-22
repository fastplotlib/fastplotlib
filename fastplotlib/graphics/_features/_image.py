from ._base import GraphicFeature, FeatureEvent

from ...utils import (
    make_colors,
    get_cmap_texture,
    quick_min_max,
)


class Vmin(GraphicFeature):
    """lower contrast limit"""
    def __init__(self, value: float):
        self._value = value
        super().__init__()

    @property
    def value(self) -> float:
        return self._value

    def set_value(self, graphic, value: float):
        vmax = graphic.world_object.material.clim[1]
        graphic.world_object.material.clim = (value, vmax)
        self._value = value

        event = FeatureEvent(type="vmin", info={"value": value})
        self._call_event_handlers(event)


class Vmax(GraphicFeature):
    """upper contrast limit"""
    def __init__(self, value: float):
        self._value = value
        super().__init__()

    @property
    def value(self) -> float:
        return self._value

    def set_value(self, graphic, value: float):
        vmin = graphic.world_object.material.clim[0]
        graphic.world_object.material.clim = (vmin, value)
        self._value = value

        event = FeatureEvent(type="vmax", info={"value": value})
        self._call_event_handlers(event)


class Cmap(GraphicFeature):
    """colormap for texture"""
    def __init__(self, value: str):
        self._value = value
        self.texture = get_cmap_texture(value)
        super().__init__()

    @property
    def value(self) -> str:
        return self._value

    def set_value(self, graphic, value: str):
        new_colors = make_colors(256, value)
        graphic.world_object.material.map.data[:] = new_colors
        graphic.world_object.material.map.data.update_range((0, 0, 0), size=(256, 1, 1))

        self._value = value
        event = FeatureEvent(type="cmap", info={"value": value})
        self._call_event_handlers(event)
