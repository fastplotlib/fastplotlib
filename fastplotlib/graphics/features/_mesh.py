from typing import Any, Sequence

import numpy as np
import pygfx

from ._base import (
    GraphicFeature,
    GraphicFeatureEvent,
    to_gpu_supported_dtype,
    block_reentrance,
)

from ._positions import VertexPositions
from ...utils.functions import get_cmap


def resolve_cmap_mesh(cmap) -> pygfx.TextureMap | None:
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


class MeshVertexPositions(VertexPositions):
    """Manages mesh vertex positions, same as VertexPosition but data must be of shape [n, 3]"""
    def _fix_data(self, data):
        if data.ndim != 2 or data.shape[1] !=3:
            raise ValueError(
                f"mesh vertex positions must be of shape: [n_vertices, 3], you passed an array of shape: {data.shape}"
            )

        return to_gpu_supported_dtype(data)


class MeshIndices(VertexPositions):
    event_info_spec = [
        {
            "dict key": "key",
            "type": "slice, index (int) or numpy-like fancy index",
            "description": "key at which vertex indices were indexed/sliced",
        },
        {
            "dict key": "value",
            "type": "int | float | array-like",
            "description": "new data values for indices that were changed",
        },
    ]

    def __init__(
        self, data: Any, isolated_buffer: bool = True, property_name: str = "indices"
    ):
        """
        Manages the vertex indices buffer shown in the graphic.
        Supports fancy indexing if the data array also supports it.
        """

        data = self._fix_data(data)
        super().__init__(
            data, isolated_buffer=isolated_buffer, property_name=property_name
        )

    def _fix_data(self, data):
        if data.ndim != 2 or data.shape[1] not in (3, 4):
            raise ValueError(
                f"indices must be of shape: [n_vertices, 3] or [n_vertices, 4], "
                f"you passed an array of shape: {data.shape}"
            )

        return data.astype("i4")


class MeshCmap(GraphicFeature):
    event_info_spec = [
        {
            "dict key": "value",
            "type": "str | dict | pygfx.TextureMap | pygfx.Texture | np.ndarray",
            "description": "new cmap",
        },
    ]

    def __init__(
            self,
            value: str | dict | pygfx.TextureMap | pygfx.Texture | np.ndarray | None,
            property_name: str = "cmap",
    ):
        """Manages a mesh colormap"""

        self._value = value
        super().__init__(property_name=property_name)

    @property
    def value(self) -> str | dict | pygfx.TextureMap | pygfx.Texture | np.ndarray | None:
        return self._value

    @block_reentrance
    def set_value(
        self, graphic, value: str | dict | pygfx.TextureMap | pygfx.Texture | np.ndarray | None
    ):
        graphic.world_object.material.map = resolve_cmap_mesh(value)
        self._value = value

        event = GraphicFeatureEvent(type=self._property_name, info={"value": value})
        self._call_event_handlers(event)
