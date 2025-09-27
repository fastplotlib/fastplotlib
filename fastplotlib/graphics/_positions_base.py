from typing import Any

import numpy as np

import pygfx
from ._base import Graphic
from .features import (
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
        """Get or set the graphic's data"""
        return self._data

    @data.setter
    def data(self, value):
        self._data[:] = value

    @property
    def colors(self) -> VertexColors | pygfx.Color:
        """Get or set the colors"""
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
        """
        Control the cmap or cmap transform

        For supported colormaps see the ``cmap`` library catalogue: https://cmap-docs.readthedocs.io/en/stable/catalog/
        """
        return self._cmap

    @cmap.setter
    def cmap(self, name: str):
        if self._cmap is None:
            raise BufferError("Cannot use cmap with uniform_colors=True")

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

    def __init__(
        self,
        data: Any,
        colors: str | np.ndarray | tuple[float] | list[float] | list[str] = "w",
        uniform_color: bool = False,
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
                self._cmap = VertexCmap(self._colors, cmap_name=None, transform=None)
            else:
                if uniform_color:
                    if not isinstance(colors, str):  # not a single color
                        if not len(colors) in [3, 4]:  # not an RGB(A) array
                            raise TypeError(
                                "must pass a single color if using `uniform_colors=True`"
                            )
                    self._colors = UniformColor(colors)
                    self._cmap = None
                else:
                    self._colors = VertexColors(
                        colors, n_colors=self._data.value.shape[0]
                    )
                    self._cmap = VertexCmap(
                        self._colors, cmap_name=None, transform=None
                    )

        self._size_space = SizeSpace(size_space)
        super().__init__(*args, **kwargs)
