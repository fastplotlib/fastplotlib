from typing import Sequence, Any

import numpy as np

import pygfx

from ._positions_base import Graphic
from .selectors import (
    LinearRegionSelector,
    LinearSelector,
    RectangleSelector,
    PolygonSelector,
)
from .features import (
    BufferManager,
    VertexPositions,
    VertexColors,
    UniformColor,
    VertexCmap,
)
from ..utils.functions import get_cmap
from ..utils import quick_min_max


def resolve_cmap(cmap):
    """Turn a user-provided in a pygfx.TextureMap, supporting 1D, 2D and 3D data."""
    if cmap is None:
        pygfx_cmap = None
    elif isinstance(cmap, pygfx.TextureMap):
        pygfx_cmap = cmap
    elif isinstance(cmap, pygfx.Texture):
        pygfx_cmap = pygfx.TextureMap(cmap)
    elif isinstance(cmap, (str, dict)):
        pygfx_cmap = pygfx.cm.create_colormap(get_cmap(cmap))
    else:
        map = np.asarray(cmap)
        if map.ndim == 2:  # 1D plus color
            pygfx_cmap = pygfx.cm.create_colormap(cmap)
        else:
            tex = pygfx.Texture(map, dim=map.ndim - 1)
            pygfx_cmap = pygfx.TextureMap(tex)

    return pygfx_cmap


class MeshGraphic(Graphic):
    _features = {
        "positions": VertexPositions,
        "indices": BufferManager,
        "mapcoords": (BufferManager, None),
        "colors": (VertexColors, UniformColor),
    }

    def __init__(
        self,
        positions: Any,
        indices: Any,
        colors: str | np.ndarray | Sequence = "w",
        mapcoords: Any = None,
        cmap: str = None,
        isolated_buffer: bool = True,
        **kwargs,
    ):
        """
        Create a mesh Graphic.

        Parameters
        ----------
        positions: array-like
            The 3D positions of the vertices.

        indices: array-like
            The indices into the positions that make up the triangles. Each 3
            subsequent indices form a triangle.

        colors: str, array, or iterable, default "w"
            A uniform color, or the per-position colors.

        mapcoords: array-like
            The per-position coordinates to which to apply the colormap (a.k.a. texcoords).
            These can e.g. be some domain-specific value, mapped to [0..1].
            If ``mapcoords`` and ``cmap`` are given, they are used instead of ``colors``.

        cmap: str, optional
            Apply a colormap to the mesh, this overrides any argument passed to
            "colors". For supported colormaps see the ``cmap`` library
            catalogue: https://cmap-docs.readthedocs.io/en/stable/catalog/
            Both 1D and 2D colormaps are supported, though the mapcoords has to match the dimensionality.

        **kwargs
            passed to :class:`.Graphic`

        """

        super().__init__(**kwargs)

        if isinstance(positions, VertexPositions):
            self._positions = positions
        else:
            self._positions = VertexPositions(
                positions, isolated_buffer=isolated_buffer, property_name="positions"
            )

        if isinstance(positions, BufferManager):
            self._indices = indices
        else:
            self._indices = BufferManager(
                indices, isolated_buffer=isolated_buffer, property_name="indices"
            )

        if mapcoords is None:
            self._mapcoords = None
        elif isinstance(mapcoords, BufferManager):
            self._mapcoords = mapcoords
        else:
            self._mapcoords = mapcoords = BufferManager(
                mapcoords, isolated_buffer=isolated_buffer, property_name="mapcoords"
            )

        uniform_color = "w"
        per_vertex_colors = False
        pygfx_cmap = resolve_cmap(cmap)
        if cmap is None:
            if colors is None:
                uniform_color = "w"
                self._colors = UniformColor(uniform_color)
            elif isinstance(colors, str) or isinstance(colors, tuple):
                uniform_color = colors
                self._colors = UniformColor(uniform_color)
            elif isinstance(colors, VertexColors):
                per_vertex_colors = True
                self._colors = colors
                self._colors._shared += 1
            else:
                per_vertex_colors = True
                self._colors = VertexColors(
                    colors, n_colors=self._positions.value.shape[0]
                )

        geometry = pygfx.Geometry(
            positions=self._positions.buffer, indices=self._indices._buffer
        )
        material = pygfx.MeshPhongMaterial(
            color_mode="uniform",
            color=uniform_color,
            pick_write=True,
        )

        # Set all the data
        if per_vertex_colors:
            geometry.colors = self._colors.buffer
        if mapcoords is not None:
            geometry.texcoords = self._mapcoords.buffer
        if pygfx_cmap is not None:
            material.map = pygfx_cmap

        # Decide on color mode
        # uniform = None  #: Use the uniform color (usually ``material.color``).
        # vertex = None  #: Use the per-vertex color specified in the geometry  (usually  ``geometry.colors``).
        # face = None  #: Use the per-face color specified in the geometry  (usually  ``geometry.colors``).
        # vertex_map = None  #: Use per-vertex texture coords (``geometry.texcoords``), and sample these in ``material.map``.
        # face_map = None  #: Use per-face texture coords (``geometry.texcoords``), and sample these in ``material.map``.
        if mapcoords is not None and pygfx_cmap is not None:
            material.color_mode = "vertex_map"
        elif per_vertex_colors:
            material.color_mode = "vertex"
        else:
            material.color_mode = "uniform"

        world_object: pygfx.Mesh = pygfx.Mesh(geometry=geometry, material=material)

        self._set_world_object(world_object)
