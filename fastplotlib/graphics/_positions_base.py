from typing import Any

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
    SizeSpace,
)
from .features.utils import is_single_color
from features.types import ColorLike, MultiColorLike


class PositionsGraphic(Graphic):
    """Base class for LineGraphic and ScatterGraphic"""

    # the feature used to manage a per-vertex color buffer, subclasses may override
    _VertexColorsCls = VertexColors

    def __init__(
        self,
        data: Any,
        colors: ColorLike | MultiColorLike = "w",
        cmap: str | cmap_lib.ColormapLike | None = None,
        cmap_transform: np.ndarray | None = None,
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
        self._colors = None

        if cmap is not None:
            # if a cmap is specified it overrides colors argument
            self._cmap, self._cmap_transform = self._create_cmap_buffers(cmap, cmap_transform)

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
        new_mode = "uniform" if is_single_color(value) else "vertex"
        old_mode = self._color_mode
        ColorsCls = {
            "uniform": UniformColor,
            "vertex": self._VertexColorsCls
        }.get(new_mode)

        if isinstance(self._colors, ColorsCls):
            # it's already the right instance type
            self._colors.set_value(self, value)
            return

        # clear any event handlers from old feature
        if self._colors is not None:
            self._colors.clear_event_handlers()

        if self._cmap is not None:
            self._cmap.clear_event_handlers()
            self._cmap_transform.clear_event_handlers()
            self._cmap = None
            self._cmap_transform = None

        # create the new buffer and set
        self._colors = self._create_colors_buffer(value)

        match new_mode:
            case "uniform":
                self.world_object.material.color = self._colors.value
                self.world_object.material.color_mode = "uniform"
                self.world_object.geometry.colors = None
            case "vertex":
                self.world_object.geometry.colors = self._colors._fpl_buffer
                self.world_object.material.color_mode = "vertex"
                self.world_object.material.color = None

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
        self._cmap, self._cmap_transform = self._create_cmap_buffers(value, self.cmap_transform)

        # set stuff on wo
        self.world_object.material.map = self._cmap.value.to_pygfx()
        self.world_object.geometry.texcoords = pygfx.Buffer(self._cmap_transform.value)
        self.world_object.material.color_mode = "vertex_map"

        # clear any other color info
        if self._colors is not None:
            self._colors.clear_event_handlers()
            self.world_object.geometry.colors = None
            self.world_object.material.color = None
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

        if isinstance(colors, VertexColors, UniformColor):
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

    def _create_cmap_buffers(self, cmap, cmap_transform) -> tuple[VertexCmap, VertexCmapTransform]:
        cmap = VertexCmap(cmap)

        if cmap_transform is None:
            # default transform is just a linspace along the datapoints
            cmap_transform = np.linspace(0, 1, len(self))
        else:
            if len(cmap_transform) != len(self):
                raise ValueError("`cmap_transform` must be a 1D array of the same size as the number of datapoints")

        cmap_transform = VertexCmapTransform(cmap_transform)

        return cmap, cmap_transform

    def format_pick_info(self, pick_info: dict) -> str:
        index = pick_info["vertex_index"]
        info = "\n".join(
            f"{dim}: {val:.4g}" for dim, val in zip("xyz", self.data[index])
        )

        return info

    def __len__(self) -> int:
        """number of datapoints"""
        return len(self.data)
