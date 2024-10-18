from typing import Any

import numpy as np

import pygfx
from ._base import Graphic
from ._features import (
    VertexPositions,
    VertexColors,
    UniformColor,
    UniformAlpha,
    VertexAlpha,
    VertexCmap,
    VertexCmapTransform,
    PointsSizesFeature,
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

            # invalidate any cmap, cmap_transform, or alpha that have been set
            self._cmap._value = None
            self._cmap_transform._value = None

            alphas = np.unique(self._colors[:, -1])
            # invalidate alpha if it is different between vertices
            if alphas.size == 1:
                self._alpha._value = alphas[0]
            else:
                self._alpha._value = None

        elif isinstance(self._colors, UniformColor):
            self._colors.set_value(self, value)

            # push the alpha value
            self._alpha._value = np.array(self.colors)[-1]

    @property
    def cmap(self) -> str:
        """Get or set the colormap"""
        if self._cmap is None:
            raise BufferError("Cannot use cmap with uniform_colors=True")

        return self._cmap.value

    @cmap.setter
    def cmap(self, name: str):
        if self._cmap is None:
            raise BufferError("Cannot use cmap with uniform_colors=True")

        self._cmap.set_value(self, name)

    @property
    def cmap_transform(self) -> np.ndarray:
        """Get or set the colormap transform"""
        if self._cmap is None:
            raise BufferError("Cannot use cmap_transform with uniform_colors=True")

        return self._cmap_transform.value

    @cmap_transform.setter
    def cmap_transform(self, transform: np.ndarray):
        if self._cmap is None:
            raise BufferError("Cannot use cmap_transform with uniform_colors=True")

        self._cmap_transform.set_value(self, transform)

    @property
    def alpha(self) -> float:
        """Get or set the alpha (transparency) value"""
        return self._alpha.value

    @alpha.setter
    def alpha(self, value: float):
        self._alpha.set_value(self, value)

    def __init__(
        self,
        data: Any,
        colors: str | np.ndarray | tuple[float] | list[float] | list[str] = "w",
        uniform_color: bool = False,
        alpha: float = 1.0,
        cmap: str | VertexCmap = None,
        cmap_transform: np.ndarray = None,
        isolated_buffer: bool = True,
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

                    self._cmap_transform = VertexCmapTransform(
                        cmap_transform,
                        vertex_colors=self._colors,
                    )
                    self._alpha = VertexAlpha(alpha, vertex_colors=self._colors)
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
                    self._alpha = UniformAlpha(alpha, uniform_colors=self._colors)
                    self._cmap = None
                    self._cmap_transform = None
                else:
                    self._colors = VertexColors(
                        colors,
                        n_colors=self._data.value.shape[0],
                        alpha=alpha,
                    )
                    self._cmap = VertexCmap(
                        self._colors, cmap_name=None, transform=None, alpha=alpha
                    )
                    self._cmap_transform = VertexCmapTransform(None, vertex_colors=self._colors)
                    self._alpha = VertexAlpha(alpha, vertex_colors=self._colors)

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
