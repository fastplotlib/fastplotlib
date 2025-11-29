from typing import Sequence, Any, Literal

import numpy as np

import pygfx

from ._positions_base import Graphic
from .features import (
    MeshVertexPositions,
    MeshIndices,
    MeshCmap,
    VertexColors,
    UniformColor,
    resolve_cmap_mesh,
    VolumeSlicePlane,
)


class MeshGraphic(Graphic):
    _features = {
        "positions": MeshVertexPositions,
        "indices": MeshIndices,
        "colors": (VertexColors, UniformColor),
        "cmap": MeshCmap,
    }

    def __init__(
        self,
        positions: Any,
        indices: Any,
        mode: Literal["basic", "phong", "slice"],
        plane: tuple[float, float, float, float] = (0, 0, 1, 0),
        colors: str | np.ndarray | Sequence = "w",
        mapcoords: Any = None,
        cmap: str | dict | pygfx.Texture | pygfx.TextureMap | np.ndarray = None,
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
            An image can also be used, this is basically a 2D colormap.

        **kwargs
            passed to :class:`.Graphic`

        """

        super().__init__(**kwargs)

        if isinstance(positions, MeshVertexPositions):
            self._positions = positions
        else:
            self._positions = MeshVertexPositions(
                positions, isolated_buffer=isolated_buffer, property_name="positions"
            )

        if isinstance(positions, MeshIndices):
            self._indices = indices
        else:
            self._indices = MeshIndices(
                indices, isolated_buffer=isolated_buffer, property_name="indices"
            )

        self._cmap = MeshCmap(cmap)

        if mapcoords is not None:
            self._mapcoords = pygfx.Buffer(np.asarray(mapcoords, dtype=np.float32))
        else:
            self._mapcoords = None

        uniform_color = "w"
        per_vertex_colors = False

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
            else:
                per_vertex_colors = True
                self._colors = VertexColors(
                    colors, n_colors=self._positions.value.shape[0]
                )

        geometry = pygfx.Geometry(
            positions=self._positions.buffer, indices=self._indices._buffer
        )

        valid_modes = ["basic", "phong", "slice"]
        if mode not in valid_modes:
            raise ValueError(f"mode must be one of: {valid_modes}\nYou passed: {mode}")
        self._mode = mode

        material_cls = getattr(pygfx, f"Mesh{mode.capitalize()}Material")

        if mode == "slice":
            self._plane = VolumeSlicePlane(plane)
            add_kwargs = {"plane": self._plane.value}
        else:
            # for basic and phong, maybe later we can add more of the properties
            add_kwargs = {}

        material = material_cls(
            color_mode="uniform",
            color=uniform_color,
            pick_write=True,
            **add_kwargs,
        )

        # Set all the data
        if per_vertex_colors:
            geometry.colors = self._colors.buffer
        if self._mapcoords is not None:
            geometry.texcoords = self._mapcoords
        elif self._cmap.value is not None:
            material.map = resolve_cmap_mesh(self.cmap)

        # Decide on color mode
        # uniform = None  #: Use the uniform color (usually ``material.color``).
        # vertex = None  #: Use the per-vertex color specified in the geometry  (usually  ``geometry.colors``).
        # face = None  #: Use the per-face color specified in the geometry  (usually  ``geometry.colors``).
        # vertex_map = None  #: Use per-vertex texture coords (``geometry.texcoords``), and sample these in ``material.map``.
        # face_map = None  #: Use per-face texture coords (``geometry.texcoords``), and sample these in ``material.map``.
        if mapcoords is not None and self._cmap.value is not None:
            material.color_mode = "vertex_map"
        elif per_vertex_colors:
            material.color_mode = "vertex"
        else:
            material.color_mode = "uniform"

        world_object: pygfx.Mesh = pygfx.Mesh(geometry=geometry, material=material)

        self._set_world_object(world_object)

    @property
    def mode(self) -> Literal["basic", "phong", "slice"]:
        return self._mode

    @property
    def positions(self) -> MeshVertexPositions:
        """Get or set the vertex positions"""
        return self._positions

    @positions.setter
    def positions(self, new_positions):
        self._positions[:] = new_positions

    @property
    def indices(self) -> MeshIndices:
        """Get or set the vertex indices"""
        return self._indices

    @indices.setter
    def indices(self, mew_indices):
        self._indices[:] = mew_indices

    @property
    def mapcoords(self) -> np.ndarray | None:
        if self._mapcoords is not None:
            return self._mapcoords.data

    @mapcoords.setter
    def mapcoords(self, new_mapcoords: np.ndarray | None):
        if new_mapcoords is None:
            self.world_object.geometry.texcoords = None
            self._mapcoords = None
            return

        if new_mapcoords.shape == self._mapcoords.data.shape:
            self._mapcoords.data[:] = new_mapcoords
            self._mapcoords.update_full()
        else:
            # allocate new buffer
            self._mapcoords = pygfx.Buffer(np.asarray(new_mapcoords, dtype=np.float32))
            self.world_object.geometry.texcoords = self._mapcoords

    @property
    def colors(self) -> VertexColors | pygfx.Color:
        """Get or set the colors"""
        if isinstance(self._colors, VertexColors):
            return self._colors

        elif isinstance(self._colors, UniformColor):
            return self._colors.value

    @colors.setter
    def colors(self, value: str | np.ndarray | Sequence[float] | Sequence[str]):
        if isinstance(self._colors, VertexColors):
            self._colors[:] = value

        elif isinstance(self._colors, UniformColor):
            self._colors.set_value(self, value)

    @property
    def cmap(self) -> str | dict | pygfx.Texture | pygfx.TextureMap | np.ndarray | None:
        if self._cmap is not None:
            return self._cmap.value

    @cmap.setter
    def cmap(self, new_cmap: str | dict | pygfx.Texture | pygfx.TextureMap | np.ndarray | None):
        self._cmap.set_value(self, new_cmap)

    @property
    def plane(self) -> tuple[float, float, float, float] | None:
        """Get or set displayed plane in the volume. Valid only for `slice` render mode."""
        if self.mode != "slice":
            return

        return self._plane.value

    @plane.setter
    def plane(self, value: tuple[float, float, float, float]):
        if self.mode != "slice":
            raise TypeError("`plane` property is only valid for `slice` render mode.")

        self._plane.set_value(self, value)

