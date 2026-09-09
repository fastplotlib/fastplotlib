from collections.abc import Iterable
from typing import Any, Literal

import numpy as np
import cmap as cmap_lib

import pygfx
from ._base import Graphic
from .features import (
    VertexPositions,
    VertexColors,
    UniformColor,
    VertexCmap,
    VertexCmapTransform,
    VertexCmapRange,
    SizeSpace,
)
from .features.utils import is_single_color
from .features.types import ColorLike, MultiColorLike, ColormapLike


class PositionsGraphic(Graphic):
    """Base class for LineGraphic and ScatterGraphic"""

    # features shared by all positions graphics; subclasses add their own in __init_subclass__
    _features = {
        "data": VertexPositions,
        "colors": (VertexColors, UniformColor),
        "cmap": (VertexCmap, None),  # none if UniformColor
        "cmap_transform": (VertexCmapTransform, None),
        "cmap_range": (VertexCmapRange, None),
        "size_space": SizeSpace,
    }

    # the feature used to manage a per-vertex color buffer, subclasses may override
    _VertexColorsCls = VertexColors

    def __init_subclass__(cls, **kwargs):
        # accumulate the parent's features, then this subclass's own additions/overrides
        inherited = {}
        for base in cls.__bases__:
            inherited.update(getattr(base, "_features", {}))
        # cls.__dict__, not cls._features, so this is only what the subclass declares (not inherited)
        own = cls.__dict__.get("_features", {})
        cls._features = {**inherited, **own}
        super().__init_subclass__(**kwargs)  # Graphic.__init_subclass__ adds the common features

    def __init__(
        self,
        data: Any,
        colors: ColorLike | MultiColorLike = "w",
        cmap: ColormapLike | None = None,
        cmap_transform: np.ndarray | Iterable[int | float] | None = None,
        cmap_range: tuple[float, float] | None = None,
        size_space: str = "screen",
        *args,
        **kwargs,
    ):
        if isinstance(data, VertexPositions):
            self._data = data
        else:
            self._data = VertexPositions(data)

        if cmap_transform is not None and cmap is None:
            raise ValueError("must pass `cmap` if passing `cmap_transform`")

        # defaults are None
        self._cmap = None
        self._cmap_transform = None
        self._cmap_range = None
        self._colors = None

        if cmap is not None:
            # if a cmap is specified it overrides colors argument
            self._cmap, self._cmap_transform, self._cmap_range = self._create_cmap_buffers(
                cmap, cmap_transform, cmap_range
            )

        else:
            # no cmap given
            self._colors = self._create_colors_buffer(colors)

        self._size_space = SizeSpace(size_space)
        super().__init__(*args, **kwargs)

    @property
    def data(self) -> VertexPositions:
        """
        Get or set the graphic's data.

        Note that if the number of datapoints does not match the number of
        current datapoints a new buffer is automatically allocated. This can
        have performance drawbacks when you have a very large number of datapoints.
        This is usually fine as long as you don't need to do it hundreds of times
        per second.
        """
        return self._data

    @data.setter
    def data(self, value):
        self._data.set_value(self, value)

    @property
    def colors(self) -> VertexColors | pygfx.Color | None:
        """Get or set the colors"""
        if isinstance(self._colors, VertexColors):
            return self._colors

        elif isinstance(self._colors, UniformColor):
            return self._colors.value

    @colors.setter
    def colors(self, value: ColorLike | MultiColorLike):
        # currently per-vertex: stay per-vertex, broadcasting a single color or setting a sequence
        if isinstance(self._colors, VertexColors):
            self._colors.set_value(self, value)
            return

        # currently uniform: a single color stays uniform, a sequence switches to per-vertex
        if isinstance(self._colors, UniformColor) and is_single_color(value):
            self._colors.set_value(self, value)
            return

        # otherwise switch: from uniform to per-vertex, or away from a cmap
        old_mode = self._color_mode

        if self._colors is not None:
            self._colors.clear_event_handlers()

        if self._cmap is not None:
            self._cmap.clear_event_handlers()
            self._cmap_transform.clear_event_handlers()
            self._cmap = None
            self._cmap_transform = None

        # create the new buffer and set
        self._colors = self._create_colors_buffer(value)

        if isinstance(self._colors, VertexColors):
            self.world_object.geometry.colors = self._colors._fpl_buffer
            self.world_object.material.color_mode = "vertex"
            self.world_object.material.color = (1, 1, 1, 1)  # back to default, material.color cannot be None
        else:
            self.world_object.material.color = self._colors.value
            self.world_object.material.color_mode = "uniform"
            self.world_object.geometry.colors = None

        if old_mode == "vertex_map":
            # clear cmap world object stuff: map and texcoords
            self.world_object.material.map = None
            self.world_object.geometry.texcoords = None

    @property
    def _color_mode(self) -> pygfx.enums.ColorMode:
        """
        Get the current color mode.
        """
        return self.world_object.material.color_mode

    @property
    def cmap(self) -> cmap_lib.Colormap | None:
        """
        Get or set the colormap

        For supported colormaps see the ``cmap`` library catalogue: https://cmap-docs.readthedocs.io/en/stable/catalog/
        """
        if self._cmap is not None:
            return self._cmap.value

    @cmap.setter
    def cmap(self, value: cmap_lib.ColormapLike):
        if self._cmap is not None:
            self._cmap.set_value(self, value)
            return

        # need to create cmap features
        self._cmap, self._cmap_transform, self._cmap_range = self._create_cmap_buffers(
            value, self.cmap_transform, self.cmap_range
        )

        # set stuff on wo
        self.world_object.material.map = self._cmap.value.to_pygfx()
        self.world_object.geometry.texcoords = pygfx.Buffer(self._cmap_transform.value)
        self.world_object.material.color_mode = "vertex_map"
        self.world_object.material.maprange = self._cmap_range.value

        # clear any other color info
        if self._colors is not None:
            self._colors.clear_event_handlers()
            self.world_object.geometry.colors = None
            self.world_object.material.color = (1, 1, 1, 1)  # back to default, material.color cannot be None
            self._colors = None

    @property
    def cmap_transform(self) -> np.ndarray | None:
        # TODO: if a usecase arises in the future we can make this a BufferManager instead of a simple GraphicFeature
        if self._cmap_transform is not None:
            return self._cmap_transform.value

    @cmap_transform.setter
    def cmap_transform(self, value: np.ndarray):
        if self._cmap is None:
            raise AttributeError("Must set `cmap` before setting `cmap_transform`")

        self._cmap_transform.set_value(self, value)
        # new default range from the new transform's (min, max)
        transform = self._cmap_transform.value
        self._cmap_range.set_value(self, (transform.min(), transform.max()))

    @property
    def cmap_range(self) -> tuple[float, float] | None:
        """Get or set the (min, max) of the cmap_transform that is mapped onto the colormap"""
        if self._cmap_range is not None:
            return self._cmap_range.value

    @cmap_range.setter
    def cmap_range(self, value: tuple[float, float]):
        if self._cmap is None:
            raise AttributeError("Must set `cmap` before setting `cmap_range`")
        self._cmap_range.set_value(self, value)

    @property
    def size_space(self):
        """
        The coordinate space in which the size is expressed ('screen', 'world', 'model')

        See https://docs.pygfx.org/stable/_autosummary/utils/utils/enums/pygfx.utils.enums.CoordSpace.html#pygfx.utils.enums.CoordSpace for available options.
        """
        return self._size_space.value

    @size_space.setter
    def size_space(self, value: str):
        self._size_space.set_value(self, value)

    def _create_colors_buffer(self, colors) -> UniformColor | VertexColors:
        # creates either a UniformColor or VertexColors based on the given `colors`

        if isinstance(colors, (VertexColors, UniformColor)):
            # share buffer with existing colors instance
            return colors

        # determine if a single or multiple colors were passed and decide color mode
        if is_single_color(colors):
            # one color specified as a str or pygfx.Color, or one color specified with RGB(A) values
            return UniformColor(colors)

        else:
            # sequence of colors
            return self._VertexColorsCls(
                colors, n_colors=self._data.value.shape[0]
            )

    def _create_cmap_buffers(
        self, cmap, cmap_transform, cmap_range
    ) -> tuple[VertexCmap, VertexCmapTransform, VertexCmapRange]:
        cmap = VertexCmap(cmap)

        if cmap_transform is None:
            # default transform is just a linspace along the datapoints
            # this gets interpolated based on the number of datapoints
            cmap_transform = np.array([0, 1])

        # the raw transform is stored as texcoords; the material's maprange maps it onto the colormap
        cmap_transform = VertexCmapTransform(
            cmap_transform,
            # use buffer array length since len(self.data) returns half for inflines
            n_datapoints=len(self.data.buffer.data)
        )

        if cmap_range is None:
            # default range is the transform's own (min, max), like the default [0, 1] transform
            cmap_range = cmap_transform.value.min(), cmap_transform.value.max()

        cmap_range = VertexCmapRange(cmap_range)

        return cmap, cmap_transform, cmap_range

    def _get_material_kwargs(self) -> dict:
        # material kwargs shared by all positions graphics; the color mode is
        # determined by the current color/cmap state, subclasses add their own kwargs
        kwargs = dict(
            pick_write=True,
            aa=self.alpha_mode in ("blend", "weighted_blend"),
            depth_compare="<=",
        )

        if self._cmap is not None:
            kwargs["color_mode"] = "vertex_map"
            kwargs["map"] = self.cmap.to_pygfx()
            kwargs["maprange"] = self._cmap_range.value
        elif isinstance(self._colors, UniformColor):
            kwargs["color_mode"] = "uniform"
            kwargs["color"] = self.colors
        else:
            kwargs["color_mode"] = "vertex"

        return kwargs

    def _get_geo_kwargs(self) -> dict:
        # geometry kwargs shared by all positions graphics, subclasses add their own kwargs
        kwargs = dict(positions=self._data._fpl_buffer)

        if self._cmap is not None:
            # cmap overrides colors, uses per-vertex texcoords into the colormap
            kwargs["texcoords"] = pygfx.Buffer(self._cmap_transform.value)
        elif isinstance(self._colors, VertexColors):
            kwargs["colors"] = self._colors._fpl_buffer
        # uniform color needs no geometry buffer

        return kwargs

    def _make_geo(self) -> pygfx.Geometry:
        return pygfx.Geometry(**self._get_geo_kwargs())

    def format_pick_info(self, pick_info: dict) -> str:
        index = pick_info["vertex_index"]
        info = "\n".join(
            f"{dim}: {val:.4g}" for dim, val in zip("xyz", self.data[index])
        )

        return info

    def __len__(self) -> int:
        """number of datapoints"""
        return len(self.data)
