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
from ...utils.triangulation import triangulate


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
        if data.shape == (3,):
            pass
        elif data.ndim != 2 or data.shape[1] not in (3, 4):
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
    def value(
        self,
    ) -> str | dict | pygfx.TextureMap | pygfx.Texture | np.ndarray | None:
        return self._value

    @block_reentrance
    def set_value(
        self,
        graphic,
        value: str | dict | pygfx.TextureMap | pygfx.Texture | np.ndarray | None,
    ):
        graphic.world_object.material.map = resolve_cmap_mesh(value)
        self._value = value

        event = GraphicFeatureEvent(type=self._property_name, info={"value": value})
        self._call_event_handlers(event)


def surface_data_to_mesh(data: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    surface data to mesh positions and indices

    expects data that is of shape: [m, n, 3] or [m, n]
    """

    data = np.asarray(data)

    if data.ndim == 2:
        # "image" of z values passed
        # [m, n] -> [n_vertices, 3]
        y = (
            np.arange(data.shape[0])
            .reshape(data.shape[0], 1)
            .repeat(data.shape[1], axis=1)
        )
        x = (
            np.arange(data.shape[1])
            .reshape(1, data.shape[1])
            .repeat(data.shape[0], axis=0)
        )
        positions = np.column_stack((x.ravel(), y.ravel(), data.ravel()))
    else:
        if data.ndim != 3:
            raise ValueError(
                f"expect data that is of shape: [m, n, 3], [m, n]\n"
                f"you passed: {data.shape}"
            )
        if data.shape[2] != 3:
            raise ValueError(
                f"expect data that is of shape: [m, n, 3], [m, n]\n"
                f"you passed: {data.shape}"
            )

        # [m, n, 3] -> [n_vertices, 3]
        positions = data.reshape(-1, 3)

    # Create faces
    w = data.shape[1]
    i = np.arange(data.shape[0] - 1)
    j = np.arange(w - 1)

    j, i = np.meshgrid(j, i, indexing="ij")
    start = j.ravel() + w * i.ravel()

    indices = np.column_stack([start, start + 1, start + w + 1, start + w])

    return positions, indices


class SurfaceData(GraphicFeature):
    event_info_spec = [
        {
            "dict key": "value",
            "type": "np.ndarray",
            "description": "new surface data",
        },
    ]

    def __init__(self, value: np.ndarray | Sequence, property_name: str = "data"):
        self._value = np.asarray(value, dtype=np.float32)
        super().__init__(property_name=property_name)

    @property
    def value(self) -> np.ndarray:
        return self._value

    @block_reentrance
    def set_value(self, graphic, value: np.ndarray):
        positions, indices = surface_data_to_mesh(value)

        graphic.positions = positions
        graphic.indices = indices

        # if cmap is a 1D texture we need to set the texcoords again using new z values
        if graphic.world_object.material.map is not None:
            if graphic.world_object.material.map.texture.dim == 1:
                mapcoords = positions[:, 2]

                if graphic.clim is None:
                    clim = mapcoords.min(), mapcoords.max()
                else:
                    clim = graphic.clim
                mapcoords = (mapcoords - clim[0]) / (clim[1] - clim[0])
                graphic.mapcoords = mapcoords

        self._value = value

        event = GraphicFeatureEvent(type=self._property_name, info={"value": value})
        self._call_event_handlers(event)


def triangulate_polygon(data: np.ndarray | Sequence):
    """vertices of shape [n_vertices , 2] -> positions, indices"""
    data = np.asarray(data, dtype=np.float32)

    err_msg = (
        f"polygon vertex data must be of shape [n_vertices, 2], you passed: {data}"
    )

    if data.ndim != 2:
        raise ValueError(err_msg)
    if data.shape[1] != 2:
        raise ValueError(err_msg)

    if len(data) >= 3:
        indices = triangulate(data)
    else:
        indices = np.arange((0, 3), np.int32)

    data = np.column_stack([data, np.zeros(data.shape[0], dtype=np.float32)])

    return data, indices


class PolygonData(GraphicFeature):
    event_info_spec = [
        {
            "dict key": "value",
            "type": "np.ndarray",
            "description": "new polygon vertex data",
        },
    ]

    def __init__(self, value: np.ndarray, property_name: str = "data"):
        self._value = np.asarray(value, dtype=np.float32)
        super().__init__(property_name=property_name)

    @property
    def value(self) -> np.ndarray:
        return self._value

    @block_reentrance
    def set_value(self, graphic, value: np.ndarray | Sequence):
        value = np.asarray(value, dtype=np.float32)

        positions, indices = triangulate_polygon(value)

        geometry = graphic.world_object.geometry

        # Need larger buffer?
        if len(positions) > geometry.positions.nitems:
            arr = np.zeros((geometry.positions.nitems * 2, 3), np.float32)
            geometry.positions = pygfx.Buffer(arr)
        if len(indices) > geometry.indices.nitems:
            arr = np.zeros((geometry.indices.nitems * 2, 3), np.int32)
            geometry.indices = pygfx.Buffer(arr)

        geometry.positions.data[: len(positions)] = positions
        geometry.positions.data[len(positions) :] = (
            positions[-1] if len(positions) else (0, 0, 0)
        )
        geometry.positions.draw_range = 0, len(positions)
        geometry.positions.update_full()

        geometry.indices.data[: len(indices)] = indices
        geometry.indices.data[len(indices) :] = 0
        geometry.indices.draw_range = 0, len(indices)
        geometry.indices.update_full()

        # send event
        if len(self._event_handlers) < 1:
            return

        event = GraphicFeatureEvent(self._property_name, {"value": self.value})

        # calls any events
        self._call_event_handlers(event)
