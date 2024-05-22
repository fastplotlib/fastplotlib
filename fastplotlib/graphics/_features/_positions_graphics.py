from typing import Any

import numpy as np
import pygfx

from ...utils import (
    parse_cmap_values,
)
from ._base import (
    GraphicFeature,
    BufferManager,
    FeatureEvent,
    to_gpu_supported_dtype,
)
from .utils import parse_colors


class VertexColors(BufferManager):
    """
    Manages the color buffer for :class:`LineGraphic` or :class:`ScatterGraphic`
    """

    def __init__(
        self,
        colors: str | np.ndarray | tuple[float] | list[float] | list[str],
        n_colors: int,
        alpha: float = None,
        isolated_buffer: bool = True,
    ):
        """
        ColorFeature

        Parameters
        ----------
        colors: str | np.ndarray | tuple[float, float, float, float] | list[str] | list[float] | int | float
            specify colors as a single human-readable string, RGBA array,
            or an iterable of strings or RGBA arrays

        n_colors: int
            number of colors, if passing in a single str or single RGBA array

        alpha: float, optional
            alpha value for the colors

        """
        data = parse_colors(colors, n_colors, alpha)
        
        super().__init__(data=data, isolated_buffer=isolated_buffer)

    def __setitem__(
            self,
            key: int | slice | np.ndarray[int | bool] | tuple[slice, ...],
            value: str | np.ndarray | tuple[float] | list[float] | list[str]
    ):
        if isinstance(key, tuple):
            # directly setting RGBA values for points, we do no parsing
            if not isinstance(value, (int, float, np.ndarray)):
                raise TypeError(
                    "Can only set from int, float, or array to set colors directly by slicing the entire array"
                )

        elif isinstance(key, int):
            # set color of one point
            n_colors = 1
            value = parse_colors(value, n_colors)

        elif isinstance(key, slice):
            # find n_colors by converting slice to range and then parse colors
            start, stop, step = key.indices(self.value.shape[0])

            n_colors = len(range(start, stop, step))

            value = parse_colors(value, n_colors)

        elif isinstance(key, (np.ndarray, list)):
            if isinstance(key, list):
                # convert to array
                key = np.array(key)

            # make sure it's 1D
            if not key.ndim == 1:
                raise TypeError("If slicing colors with an array, it must be a 1D bool or int array")

            if key.dtype == bool:
                # make sure len is same
                if not key.size == self.buffer.data.shape[0]:
                    raise IndexError
                n_colors = np.count_nonzero(key)

            elif np.issubdtype(key.dtype, np.integer):
                n_colors = key.size

            else:
                raise TypeError("If slicing colors with an array, it must be a 1D bool or int array")

            value = parse_colors(value, n_colors)

        else:
            raise TypeError

        self.buffer.data[key] = value

        self._update_range(key)

        self._emit_event("colors", key, value)


class UniformColor(GraphicFeature):
    def __init__(self, value: str | np.ndarray | tuple | list | pygfx.Color):
        self._value = pygfx.Color(value)
        super().__init__()
        
    @property
    def value(self) -> pygfx.Color:
        return self._value

    def set_value(self, graphic, value: str | np.ndarray | tuple | list | pygfx.Color):
        value = pygfx.Color(value)
        graphic.world_object.material.color = value
        self._value = value

        event = FeatureEvent(type="colors", info={"value": value})
        self._call_event_handlers(event)


class UniformSizes(GraphicFeature):
    def __init__(self, value: int | float):
        self._value = float(value)
        super().__init__()

    @property
    def value(self) -> float:
        return self._value

    def set_value(self, graphic, value: str | np.ndarray | tuple | list | pygfx.Color):
        value = pygfx.Color(value)
        graphic.world_object.material.size = value
        self._value = value

        event = FeatureEvent(type="sizes", info={"value": value})
        self._call_event_handlers(event)


class VertexPositions(BufferManager):
    """
    Manages the vertex positions buffer shown in the graphic.
    Supports fancy indexing if the data array also supports it.
    """

    def __init__(self, data: Any, isolated_buffer: bool = True):
        data = self._fix_data(data)
        super().__init__(data, isolated_buffer=isolated_buffer)

    def _fix_data(self, data):
        # data = to_gpu_supported_dtype(data)

        if data.ndim == 1:
            # if user provides a 1D array, assume these are y-values
            data = np.column_stack([np.arange(data.size, dtype=data.dtype), data])

        if data.shape[1] != 3:
            if data.shape[1] != 2:
                raise ValueError(f"Must pass 1D, 2D or 3D data")

            # zeros for z
            zs = np.zeros(data.shape[0], dtype=data.dtype)

            # column stack [x, y, z] to make data of shape [n_points, 3]
            data = np.column_stack([data[:, 0], data[:, 1], zs])

        return to_gpu_supported_dtype(data)

    def __setitem__(self, key: int | slice | range | np.ndarray[int | bool] | tuple[slice, ...] | tuple[range, ...], value):
        # directly use the key to slice the buffer
        self.buffer.data[key] = value

        # _update_range handles parsing the key to
        # determine offset and size for GPU upload
        self._update_range(key)

        self._emit_event("data", key, value)


class PointsSizesFeature(BufferManager):
    """
    Access to the vertex buffer data shown in the graphic.
    Supports fancy indexing if the data array also supports it.
    """

    def __init__(
            self,
            sizes: int | float | np.ndarray | list[int | float] | tuple[int | float],
            n_datapoints: int,
            isolated_buffer: bool = True
    ):
        sizes = self._fix_sizes(sizes, n_datapoints)
        super().__init__(data=sizes, isolated_buffer=isolated_buffer)

    def _fix_sizes(self, sizes: int | float | np.ndarray | list[int | float] | tuple[int | float], n_datapoints: int):
        if np.issubdtype(type(sizes), np.number):
            # single value given
            sizes = np.full(
                n_datapoints, sizes, dtype=np.float32
            )  # force it into a float to avoid weird gpu errors

        elif isinstance(
            sizes, (np.ndarray, tuple, list)
        ):  # if it's not a ndarray already, make it one
            sizes = np.asarray(sizes, dtype=np.float32)  # read it in as a numpy.float32
            if (sizes.ndim != 1) or (sizes.size != n_datapoints):
                raise ValueError(
                    f"sequence of `sizes` must be 1 dimensional with "
                    f"the same length as the number of datapoints"
                )

        else:
            raise TypeError("sizes must be a single <int>, <float>, or a sequence (array, list, tuple) of int"
                            "or float with the length equal to the number of datapoints")

        if np.count_nonzero(sizes < 0) > 1:
            raise ValueError(
                "All sizes must be positive numbers greater than or equal to 0.0."
            )

        return sizes

    def __setitem__(self, key, value):
        # this is a very simple 1D buffer, no parsing required, directly set buffer
        self.buffer.data[key] = value
        self._update_range(key)

        self._emit_event("sizes", key, value)


class Thickness(GraphicFeature):
    """line thickness"""
    def __init__(self, value: float):
        self._value = value
        super().__init__()

    @property
    def value(self) -> float:
        return self._value

    def set_value(self, graphic, value: float):
        graphic.world_object.material.thickness = value
        self._value = value

        event = FeatureEvent(type="thickness", info={"value": value})
        self._call_event_handlers(event)


class VertexCmap(BufferManager):
    """
    Sliceable colormap feature, manages a VertexColors instance and just provides a way to set colormaps.
    """

    def __init__(self, vertex_colors: VertexColors, cmap_name: str, cmap_values: np.ndarray):
        super().__init__(data=vertex_colors)

        self._vertex_colors = vertex_colors
        self._cmap_name = cmap_name
        self._cmap_values = cmap_values

    def __setitem__(self, key, cmap_name):
        if isinstance(key, slice):
            if key.step is not None:
                raise TypeError(
                    "step sized indexing not currently supported for setting VertexCmap, "
                    "continuous regions are recommended"
                )

        offset, size, n_elements = self._parse_offset_size(key)

        colors = parse_cmap_values(
            n_colors=n_elements, cmap_name=cmap_name, cmap_values=self._cmap_values
        )

        self._cmap_name = cmap_name
        self._vertex_colors[key] = colors

        self._emit_event("cmap", key, cmap_name)

    @property
    def name(self) -> str:
        return self._cmap_name

    @property
    def values(self) -> np.ndarray:
        return self._cmap_values

    @values.setter
    def values(self, values: np.ndarray | list[float | int], indices: slice | list | np.ndarray = None):
        if self._cmap_name is None:
            raise AttributeError(
                "cmap is not set, set the cmap before setting the cmap_values"
            )

        values = np.asarray(values)

        colors = parse_cmap_values(
            n_colors=self.value.shape[0], cmap_name=self._cmap_name, cmap_values=values
        )

        self._cmap_values = values

        if indices is None:
            indices = slice(None)

        self._vertex_colors[indices] = colors

        self._emit_event("cmap.name", indices, values)

#
# class HeatmapCmapFeature(ImageCmapFeature):
#     """
#     Colormap for :class:`HeatmapGraphic`
#
#     Same event pick info as :class:`ImageCmapFeature`
#     """
#
#     def _set(self, cmap_name: str):
#         # in heatmap we use one material for all ImageTiles
#         self._parent._material.map.data[:] = make_colors(256, cmap_name)
#         self._parent._material.map.update_range((0, 0, 0), size=(256, 1, 1))
#         self._name = cmap_name
#
#         self._feature_changed(key=None, new_data=self.name)
#
#     @property
#     def vmin(self) -> float:
#         """Minimum contrast limit."""
#         return self._parent._material.clim[0]
#
#     @vmin.setter
#     def vmin(self, value: float):
#         """Minimum contrast limit."""
#         self._parent._material.clim = (value, self._parent._material.clim[1])
#
#     @property
#     def vmax(self) -> float:
#         """Maximum contrast limit."""
#         return self._parent._material.clim[1]
#
#     @vmax.setter
#     def vmax(self, value: float):
#         """Maximum contrast limit."""
#         self._parent._material.clim = (self._parent._material.clim[0], value)
