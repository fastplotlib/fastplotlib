from numbers import Real
from typing import Any, Sequence, Literal
from warnings import warn

import numpy as np

import pygfx
from ._base import Graphic
from .features import (
    VertexPositions,
    VertexColors,
    UniformColor,
    VertexCmap,
    SizeSpace,
)


class PositionsGraphic(Graphic):
    """Base class for LineGraphic and ScatterGraphic"""

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
    def colors(self) -> VertexColors | pygfx.Color:
        """Get or set the colors"""
        if isinstance(self._colors, VertexColors):
            return self._colors

        elif isinstance(self._colors, UniformColor):
            return self._colors.value

    @colors.setter
    def colors(self, value: str | np.ndarray | Sequence[float] | Sequence[str]):
        self._colors.set_value(self, value)

    @property
    def color_mode(self) -> Literal["uniform", "vertex"]:
        """
        Get or set the color mode. Note that after setting the color_mode, you will have to set the `colors`
        as well for switching between 'uniform' and 'vertex' modes.
        """
        return self.world_object.material.color_mode

    @color_mode.setter
    def color_mode(self, mode: Literal["uniform", "vertex"]):
        valid = ("uniform", "vertex")
        if mode not in valid:
            raise ValueError(f"`color_mode` must be one of : {valid}")
        if mode == "vertex" and isinstance(self._colors, UniformColor):
            # uniform -> vertex
            # need to make a new vertex buffer and get rid of uniform buffer
            new_colors = self._create_colors_buffer(self._colors.value, "vertex")
            # we can't clear world_object.material.color so just set the colors buffer on the geometry
            # this doesn't really matter anyways since the lingering uniform color takes up just a few bytes
            self.world_object.geometry.colors = new_colors._fpl_buffer

        elif mode == "uniform" and isinstance(self._colors, VertexColors):
            # vertex -> uniform
            # use first vertex color and spit out a warning
            warn(
                "changing `color_mode` from vertex -> uniform, will use first vertex color "
                "for the uniform and discard the remaining color values"
            )
            new_colors = self._create_colors_buffer(self._colors.value[0], "uniform")
            self.world_object.geometry.colors = None
            self.world_object.material.color = new_colors.value

            # clear out cmap
            self._cmap.clear_event_handlers()
            self._cmap = None

        else:
            # no change, return
            return

        # restore event handlers onto the new colors feature
        new_colors._event_handlers[:] = self._colors._event_handlers
        self._colors.clear_event_handlers()
        # this should trigger gc
        self._colors = new_colors

        # this is created so that cmap can be set later
        if isinstance(self._colors, VertexColors):
            self._cmap = VertexCmap(self._colors, cmap_name=None, transform=None)

        self.world_object.material.color_mode = mode

    @property
    def cmap(self) -> VertexCmap:
        """
        Control the cmap or cmap transform

        For supported colormaps see the ``cmap`` library catalogue: https://cmap-docs.readthedocs.io/en/stable/catalog/
        """
        return self._cmap

    @cmap.setter
    def cmap(self, name: str):
        if self.color_mode == "uniform":
            raise ValueError("cannot use `cmap` with `color_mode` = 'uniform'")

        self._cmap[:] = name

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

    def _create_colors_buffer(self, colors, color_mode) -> UniformColor | VertexColors:
        # creates either a UniformColor or VertexColors based on the given `colors` and `color_mode`
        # if `color_mode` = "auto", returns {UniformColor | VertexColor} based on what the `colors` arg represents
        # if `color_mode` = "uniform", it verifies that the user `colors` input represents just 1 color
        # if `color_mode` = "vertex", always returns VertexColors regardless of whether `colors` represents >= 1 colors

        if isinstance(colors, VertexColors):
            if color_mode == "uniform":
                raise ValueError(
                    "if a `VertexColors` instance is provided for `colors`, "
                    "`color_mode` must be 'vertex' or 'auto', not 'uniform'"
                )
            # share buffer with existing colors instance
            new_colors = colors
            # blank colormap instance
            self._cmap = VertexCmap(new_colors, cmap_name=None, transform=None)

        else:
            # determine if a single or multiple colors were passed and decide color mode
            if isinstance(colors, (pygfx.Color, str)) or (
                len(colors) in [3, 4] and all(isinstance(v, Real) for v in colors)
            ):
                # one color specified as a str or pygfx.Color, or one color specified with RGB(A) values
                if color_mode in ("auto", "uniform"):
                    new_colors = UniformColor(colors)
                else:
                    new_colors = VertexColors(
                        colors, n_colors=self._data.value.shape[0]
                    )

            elif all(isinstance(c, (str, pygfx.Color)) for c in colors):
                # sequence of colors
                if color_mode == "uniform":
                    raise ValueError(
                        "You passed `color_mode` = 'uniform', but specified a sequence of multiple colors. Use "
                        "`color_mode` = 'auto' or 'vertex' for multiple colors."
                    )
                new_colors = VertexColors(colors, n_colors=self._data.value.shape[0])

            elif len(colors) > 4:
                # sequence of multiple colors, must again ensure color_mode is not uniform
                if color_mode == "uniform":
                    raise ValueError(
                        "You passed `color_mode` = 'uniform', but specified a sequence of multiple colors. Use "
                        "`color_mode` = 'auto' or 'vertex' for multiple colors."
                    )
                new_colors = VertexColors(colors, n_colors=self._data.value.shape[0])
            else:
                raise ValueError(
                    "`colors` must be a str, pygfx.Color, array, list or tuple indicating an RGB(A) color, or a "
                    "sequence of str, pygfx.Color, or array of shape [n_datapoints, 3 | 4]"
                )

        return new_colors

    def __init__(
        self,
        data: Any,
        colors: str | np.ndarray | tuple[float] | list[float] | list[str] = "w",
        cmap: str | VertexCmap = None,
        cmap_transform: np.ndarray = None,
        color_mode: Literal["auto", "uniform", "vertex"] = "auto",
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

        valid = ("auto", "uniform", "vertex")

        # default _cmap is None
        self._cmap = None

        if color_mode not in valid:
            raise ValueError(f"`color_mode` must be one of {valid}")

        if cmap is not None:
            # if a cmap is specified it overrides colors argument
            if color_mode == "uniform":
                raise ValueError(
                    "if a `cmap` is provided, `color_mode` must be 'vertex' or 'auto', not 'uniform'"
                )

            if isinstance(cmap, str):
                # make colors from cmap
                if isinstance(colors, VertexColors):
                    # share buffer with existing colors instance for the cmap
                    self._colors = colors
                else:
                    # create vertex colors buffer
                    self._colors = VertexColors("w", n_colors=self._data.value.shape[0])
                    # make cmap using vertex colors buffer
                    self._cmap = VertexCmap(
                        self._colors,
                        cmap_name=cmap,
                        transform=cmap_transform,
                    )
            elif isinstance(cmap, VertexCmap):
                # use existing cmap instance
                self._cmap = cmap
                self._colors = cmap._vertex_colors

            else:
                raise TypeError(
                    "`cmap` argument must be a <str> cmap name or an existing `VertexCmap` instance"
                )
        else:
            # no cmap given
            self._colors = self._create_colors_buffer(colors, color_mode)

            # this is created so that cmap can be set later
            if isinstance(self._colors, VertexColors):
                self._cmap = VertexCmap(self._colors, cmap_name=None, transform=None)

        self._size_space = SizeSpace(size_space)
        super().__init__(*args, **kwargs)

    def format_pick_info(self, pick_info: dict) -> str:
        index = pick_info["vertex_index"]
        info = "\n".join(
            f"{dim}: {val:.4g}" for dim, val in zip("xyz", self.data[index])
        )

        return info
