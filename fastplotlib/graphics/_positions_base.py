from typing import Any

import numpy as np

import pygfx
from ._base import Graphic
from ._features import (
    VertexPositions,
    VertexColors,
    UniformColor,
    VertexCmap,
    PointsSizesFeature,
    SizeSpace,
)


class PositionsGraphic(Graphic):
    """Base class for LineGraphic and ScatterGraphic"""

    @property
    def data(self) -> VertexPositions:
        """Get or set the vertex positions data"""
        return self._data

    @data.setter
    def data(self, value):
        self._data[:] = value

    @property
    def colors(self) -> VertexColors | pygfx.Color:
        """Get or set the colors data"""
        if isinstance(self._colors, VertexColors):
            return self._colors

        elif isinstance(self._colors, UniformColor):
            return self._colors.value

    @colors.setter
    def colors(self, value: str | np.ndarray | tuple[float] | list[float] | list[str]):
        if isinstance(self._colors, VertexColors):
            self._colors[:] = value

        elif isinstance(self._colors, UniformColor):
            self._colors.set_value(self, value)

    @property
    def cmap(self) -> VertexCmap:
        """Control the cmap, cmap transform, or cmap alpha"""
        return self._cmap

    @cmap.setter
    def cmap(self, name: str):
        if self._cmap is None:
            raise BufferError("Cannot use cmap with uniform_colors=True")

        self._cmap[:] = name

    @property
    def size_space(self):
        """
        The coordinate space in which the size is expressed (‘screen’, ‘world’, ‘model’)

        See https://docs.pygfx.org/stable/_autosummary/utils/utils/enums/pygfx.utils.enums.CoordSpace.html#pygfx.utils.enums.CoordSpace for available options.
        """
        return self._size_space.value

    @size_space.setter
    def size_space(self, value: str):
        self._size_space.set_value(self, value)

    def __init__(
        self,
        data: Any,
        colors: str | np.ndarray | tuple[float] | list[float] | list[str] = "w",
        uniform_color: bool = False,
        alpha: float = 1.0,
        cmap: str | VertexCmap = None,
        cmap_transform: np.ndarray = None,
        isolated_buffer: bool = True,
        size_space: str = "screen",
        *args,
        **kwargs,
    ):
        if isinstance(data, VertexPositions):
            self._data = data
        else:
            self._data = VertexPositions(data, isolated_buffer=isolated_buffer)

        if cmap_transform is not None and cmap is None:
            raise ValueError("must pass `cmap` if passing `cmap_transform`")

        if cmap is not None:
            # if a cmap is specified it overrides colors argument
            if uniform_color:
                raise TypeError("Cannot use cmap if uniform_color=True")

            if isinstance(cmap, str):
                # make colors from cmap
                if isinstance(colors, VertexColors):
                    # share buffer with existing colors instance for the cmap
                    self._colors = colors
                    self._colors._shared += 1
                else:
                    # create vertex colors buffer
                    self._colors = VertexColors("w", n_colors=self._data.value.shape[0])
                    # make cmap using vertex colors buffer
                    self._cmap = VertexCmap(
                        self._colors,
                        cmap_name=cmap,
                        transform=cmap_transform,
                        alpha=alpha,
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
            if isinstance(colors, VertexColors):
                # share buffer with existing colors instance
                self._colors = colors
                self._colors._shared += 1
                # blank colormap instance
                self._cmap = VertexCmap(
                    self._colors, cmap_name=None, transform=None, alpha=alpha
                )
            else:
                if uniform_color:
                    if not isinstance(colors, str):  # not a single color
                        if not len(colors) in [3, 4]:  # not an RGB(A) array
                            raise TypeError(
                                "must pass a single color if using `uniform_colors=True`"
                            )
                    self._colors = UniformColor(colors, alpha=alpha)
                    self._cmap = None
                else:
                    self._colors = VertexColors(
                        colors,
                        n_colors=self._data.value.shape[0],
                        alpha=alpha,
                    )
                    self._cmap = VertexCmap(
                        self._colors, cmap_name=None, transform=None, alpha=alpha
                    )

        self._size_space = SizeSpace(size_space)
        super().__init__(*args, **kwargs)

    def unshare_property(self, property: str):
        """unshare a shared property. Experimental and untested!"""
        if not isinstance(property, str):
            raise TypeError

        f = getattr(self, property)
        if f.shared == 0:
            raise BufferError("Cannot detach an independent buffer")

        if property == "colors" and isinstance(property, VertexColors):
            self._colors._buffer = pygfx.Buffer(self._colors.value.copy())
            self.world_object.geometry.colors = self._colors.buffer
            self._colors._shared -= 1

        elif property == "data":
            self._data._buffer = pygfx.Buffer(self._data.value.copy())
            self.world_object.geometry.positions = self._data.buffer
            self._data._shared -= 1

        elif property == "sizes":
            self._sizes._buffer = pygfx.Buffer(self._sizes.value.copy())
            self.world_object.geometry.positions = self._sizes.buffer
            self._sizes._shared -= 1

    def share_property(
        self, property: VertexPositions | VertexColors | PointsSizesFeature
    ):
        """share a property from another graphic. Experimental and untested!"""
        if isinstance(property, VertexPositions):
            # TODO: check if this causes a memory leak
            self._data._shared -= 1

            self._data = property
            self._data._shared += 1
            self.world_object.geometry.positions = self._data.buffer

        elif isinstance(property, VertexColors):
            self._colors._shared -= 1

            self._colors = property
            self._colors._shared += 1
            self.world_object.geometry.colors = self._colors.buffer

        elif isinstance(property, PointsSizesFeature):
            self._sizes._shared -= 1

            self._sizes = property
            self._sizes._shared += 1
            self.world_object.geometry.sizes = self._sizes.buffer
