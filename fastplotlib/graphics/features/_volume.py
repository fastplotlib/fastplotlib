import numpy as np
import pygfx

from ._base import GraphicFeature, GraphicFeatureEvent, block_reentrance

VOLUME_RENDER_MODES = {
    "mip": pygfx.VolumeMipMaterial,
    "minip": pygfx.VolumeMinipMaterial,
    "iso": pygfx.VolumeIsoMaterial,
    "slice": pygfx.VolumeSliceMaterial,
}


def create_volume_material_kwargs(graphic, mode: str):
    kwargs = {
        "clim": (graphic.vmin, graphic.vmax),
        "map": graphic._texture_map,
        "interpolation": graphic.interpolation,
        "pick_write": True,
    }

    if mode == "iso":
        more_kwargs = {attr: getattr(graphic, attr)
            for attr in [
                "threshold",
                "step_size",
                "substep_size",
                "emissive",
                "shininess",
            ]
        }

    elif mode == "slice":
        more_kwargs = {"plane": graphic.plane}
        print(more_kwargs)
    else:
        more_kwargs = {}

    kwargs.update(more_kwargs)
    return kwargs


class VolumeRenderMode(GraphicFeature):
    """Volume rendering mode, controls world object material"""

    event_info_spec = [
        {
            "dict key": "value",
            "type": "str",
            "description": "volume rendering mode that has been set",
        },
    ]

    def __init__(self, value: str):
        self._validate(value)
        self._value = value
        super().__init__()

    @property
    def value(self) -> str:
        return self._value

    def _validate(self, value):
        if value not in VOLUME_RENDER_MODES.keys():
            raise ValueError(
                f"Given render mode: {value} is invalid. Valid render modes are: {VOLUME_RENDER_MODES.keys()}"
            )

    @block_reentrance
    def set_value(self, graphic, value: str):
        self._validate(value)

        VolumeMaterialCls = VOLUME_RENDER_MODES[value]

        kwargs = create_volume_material_kwargs(graphic, mode=value)

        new_material = VolumeMaterialCls(**kwargs)
        # since the world object is a group
        for volume_tile in graphic.world_object.children:
            volume_tile.material = new_material

        # so we have one place to reference it
        graphic._material = new_material
        self._value = value

        event = GraphicFeatureEvent(type="mode", info={"value": value})
        self._call_event_handlers(event)


class VolumeIsoThreshold(GraphicFeature):
    """Isosurface threshold"""

    event_info_spec = [
        {
            "dict key": "value",
            "type": "float",
            "description": "new isosurface threshold",
        },
    ]

    def __init__(self, value: float):
        self._value = value
        super().__init__()

    @property
    def value(self) -> float:
        return self._value

    @block_reentrance
    def set_value(self, graphic, value: float):
        graphic._material.threshold = value
        self._value = graphic._material.threshold

        event = GraphicFeatureEvent(type="threshold", info={"value": value})
        self._call_event_handlers(event)


class VolumeIsoStepSize(GraphicFeature):
    """Isosurface step_size"""

    event_info_spec = [
        {
            "dict key": "value",
            "type": "float",
            "description": "new isosurface step_size",
        },
    ]

    def __init__(self, value: float):
        self._value = value
        super().__init__()

    @property
    def value(self) -> float:
        return self._value

    @block_reentrance
    def set_value(self, graphic, value: float):
        graphic._material.step_size = value
        self._value = graphic._material.step_size

        event = GraphicFeatureEvent(type="step_size", info={"value": value})
        self._call_event_handlers(event)


class VolumeIsoSubStepSize(GraphicFeature):
    """Isosurface substep_size"""

    event_info_spec = [
        {
            "dict key": "value",
            "type": "float",
            "description": "new isosurface step_size",
        },
    ]

    def __init__(self, value: float):
        self._value = value
        super().__init__()

    @property
    def value(self) -> float:
        return self._value

    @block_reentrance
    def set_value(self, graphic, value: float):
        graphic._material.substep_size = value
        self._value = graphic._material.substep_size

        event = GraphicFeatureEvent(type="step_size", info={"value": value})
        self._call_event_handlers(event)


class VolumeIsoEmissive(GraphicFeature):
    """Isosurface emissive color"""

    event_info_spec = [
        {
            "dict key": "value",
            "type": "pygfx.Color",
            "description": "new isosurface emissive color",
        },
    ]

    def __init__(self, value: pygfx.Color | str | tuple | np.ndarray):
        self._value = pygfx.Color(value)
        super().__init__()

    @property
    def value(self) -> pygfx.Color:
        return self._value

    @block_reentrance
    def set_value(self, graphic, value: pygfx.Color | str | tuple | np.ndarray):
        graphic._material.emissive = value
        self._value = graphic._material.emissive

        event = GraphicFeatureEvent(type="emissive", info={"value": value})
        self._call_event_handlers(event)


class VolumeIsoShininess(GraphicFeature):
    """Isosurface shininess"""

    event_info_spec = [
        {
            "dict key": "value",
            "type": "int",
            "description": "new isosurface shininess",
        },
    ]

    def __init__(self, value: int):
        self._value = value
        super().__init__()

    @property
    def value(self) -> int:
        return self._value

    @block_reentrance
    def set_value(self, graphic, value: float):
        graphic._material.shininess = value
        self._value = graphic._material.shininess

        event = GraphicFeatureEvent(type="shininess", info={"value": value})
        self._call_event_handlers(event)


class VolumeSlicePlane(GraphicFeature):
    """Volume plane"""

    event_info_spec = [
        {
            "dict key": "value",
            "type": "tuple[float, float, float, float]",
            "description": "new plane slice",
        },
    ]

    def __init__(self, value: tuple[float, float, float, float]):
        self._value = value
        super().__init__()

    @property
    def value(self) -> tuple[float, float, float, float]:
        return self._value

    @block_reentrance
    def set_value(self, graphic, value: tuple[float, float, float, float]):
        graphic._material.plane = value
        self._value = graphic._material.plane

        event = GraphicFeatureEvent(type="plane", info={"value": value})
        self._call_event_handlers(event)
