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
    block_reentrance,
)
from .utils import parse_colors


class VertexColors(BufferManager):
    """

    **info dict**
    +------------+-----------------------------------------------------------+----------------------------------------------------------------------------------+
    | dict key   | value type                                                | value description                                                                |
    +============+===========================================================+==================================================================================+
    | key        | int | slice | np.ndarray[int | bool] | tuple[slice, ...]  | key at which colors were indexed/sliced                                          |
    +------------+-----------------------------------------------------------+----------------------------------------------------------------------------------+
    | value      | np.ndarray                                                | new color values for points that were changed, shape is [n_points_changed, RGBA] |
    +------------+-----------------------------------------------------------+----------------------------------------------------------------------------------+
    | user_value | str | np.ndarray | tuple[float] | list[float] | list[str] | user input value that was parsed into the RGBA array                             |
    +------------+-----------------------------------------------------------+----------------------------------------------------------------------------------+

    """

    def __init__(
        self,
        colors: str | np.ndarray | tuple[float] | list[float] | list[str],
        n_colors: int,
        alpha: float = None,
        isolated_buffer: bool = True,
    ):
        """
        Manages the vertex color buffer for :class:`LineGraphic` or :class:`ScatterGraphic`

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

    @block_reentrance
    def __setitem__(
        self,
        key: int | slice | np.ndarray[int | bool] | tuple[slice, ...],
        user_value: str | np.ndarray | tuple[float] | list[float] | list[str],
    ):
        user_key = key

        if isinstance(key, tuple):
            # directly setting RGBA values for points, we do no parsing
            if not isinstance(user_value, (int, float, np.ndarray)):
                raise TypeError(
                    "Can only set from int, float, or array to set colors directly by slicing the entire array"
                )
            value = user_value

        elif isinstance(key, int):
            # set color of one point
            n_colors = 1
            value = parse_colors(user_value, n_colors)

        elif isinstance(key, slice):
            # find n_colors by converting slice to range and then parse colors
            start, stop, step = key.indices(self.value.shape[0])

            n_colors = len(range(start, stop, step))

            value = parse_colors(user_value, n_colors)

        elif isinstance(key, (np.ndarray, list)):
            if isinstance(key, list):
                # convert to array
                key = np.array(key)

            # make sure it's 1D
            if not key.ndim == 1:
                raise TypeError(
                    "If slicing colors with an array, it must be a 1D bool or int array"
                )

            if key.dtype == bool:
                # make sure len is same
                if not key.size == self.buffer.data.shape[0]:
                    raise IndexError(
                        f"Length of array for fancy indexing must match number of datapoints.\n"
                        f"There are {len(self.buffer.data.shape[0])} datapoints and you have passed {key.size} indices"
                    )
                n_colors = np.count_nonzero(key)

            elif np.issubdtype(key.dtype, np.integer):
                n_colors = key.size

            else:
                raise TypeError(
                    "If slicing colors with an array, it must be a 1D bool or int array"
                )

            value = parse_colors(user_value, n_colors)

        else:
            raise TypeError(
                f"invalid key for setting colors, you may set colors using integer indices, slices, or "
                f"fancy indexing using an array of integers or bool"
            )

        self.buffer.data[key] = value

        self._update_range(key)

        if len(self._event_handlers) < 1:
            return

        event_info = {
            "key": user_key,
            "value": value,
            "user_value": user_value,
        }

        event = FeatureEvent("colors", info=event_info)
        self._call_event_handlers(event)

    def __len__(self):
        return len(self.buffer.data)


# Manages uniform color for line or scatter material
class UniformColor(GraphicFeature):
    def __init__(
        self, value: str | np.ndarray | tuple | list | pygfx.Color, alpha: float = 1.0
    ):
        v = (*tuple(pygfx.Color(value))[:-1], alpha)  # apply alpha
        self._value = pygfx.Color(v)
        super().__init__()

    @property
    def value(self) -> pygfx.Color:
        return self._value

    @block_reentrance
    def set_value(self, graphic, value: str | np.ndarray | tuple | list | pygfx.Color):
        value = pygfx.Color(value)
        graphic.world_object.material.color = value
        self._value = value

        event = FeatureEvent(type="colors", info={"value": value})
        self._call_event_handlers(event)


# manages uniform size for scatter material
class UniformSize(GraphicFeature):
    def __init__(self, value: int | float):
        self._value = float(value)
        super().__init__()

    @property
    def value(self) -> float:
        return self._value

    @block_reentrance
    def set_value(self, graphic, value: float | int):
        graphic.world_object.material.size = float(value)
        self._value = value

        event = FeatureEvent(type="sizes", info={"value": value})
        self._call_event_handlers(event)


# manages the coordinate space for scatter/line
class SizeSpace(GraphicFeature):
    def __init__(self, value: str):
        self._value = value
        super().__init__()

    @property
    def value(self) -> str:
        return self._value

    @block_reentrance
    def set_value(self, graphic, value: str):
        if "Line" in graphic.world_object.material.__class__.__name__:
            graphic.world_object.material.thickness_space = value
        else:
            graphic.world_object.material.size_space = value
        self._value = value

        event = FeatureEvent(type="size_space", info={"value": value})
        self._call_event_handlers(event)


class VertexPositions(BufferManager):
    """
    +----------+----------------------------------------------------------+------------------------------------------------------------------------------------------+
    | dict key | value type                                               | value description                                                                        |
    +==========+==========================================================+==========================================================================================+
    | key      | int | slice | np.ndarray[int | bool] | tuple[slice, ...] | key at which vertex positions data were indexed/sliced                                   |
    +----------+----------------------------------------------------------+------------------------------------------------------------------------------------------+
    | value    | np.ndarray | float | list[float]                         | new data values for points that were changed, shape depends on the indices that were set |
    +----------+----------------------------------------------------------+------------------------------------------------------------------------------------------+

    """

    def __init__(self, data: Any, isolated_buffer: bool = True):
        """
        Manages the vertex positions buffer shown in the graphic.
        Supports fancy indexing if the data array also supports it.
        """

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

    @block_reentrance
    def __setitem__(
        self,
        key: int | slice | np.ndarray[int | bool] | tuple[slice, ...],
        value: np.ndarray | float | list[float],
    ):
        # directly use the key to slice the buffer
        self.buffer.data[key] = value

        # _update_range handles parsing the key to
        # determine offset and size for GPU upload
        self._update_range(key)

        self._emit_event("data", key, value)

    def __len__(self):
        return len(self.buffer.data)


class PointsSizesFeature(BufferManager):
    """
    +----------+-------------------------------------------------------------------+----------------------------------------------+
    | dict key | value type                                                        | value description                            |
    +==========+===================================================================+==============================================+
    | key      | int | slice | np.ndarray[int | bool] | list[int | bool]           | key at which point sizes indexed/sliced      |
    +----------+-------------------------------------------------------------------+----------------------------------------------+
    | value    | int | float | np.ndarray | list[int | float] | tuple[int | float] | new size values for points that were changed |
    +----------+-------------------------------------------------------------------+----------------------------------------------+
    """

    def __init__(
        self,
        sizes: int | float | np.ndarray | list[int | float] | tuple[int | float],
        n_datapoints: int,
        isolated_buffer: bool = True,
    ):
        """
        Manages sizes buffer of scatter points.
        """
        sizes = self._fix_sizes(sizes, n_datapoints)
        super().__init__(data=sizes, isolated_buffer=isolated_buffer)

    def _fix_sizes(
        self,
        sizes: int | float | np.ndarray | list[int | float] | tuple[int | float],
        n_datapoints: int,
    ):
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
            raise TypeError(
                "sizes must be a single <int>, <float>, or a sequence (array, list, tuple) of int"
                "or float with the length equal to the number of datapoints"
            )

        if np.count_nonzero(sizes < 0) > 1:
            raise ValueError(
                "All sizes must be positive numbers greater than or equal to 0.0."
            )

        return sizes

    @block_reentrance
    def __setitem__(
        self,
        key: int | slice | np.ndarray[int | bool] | list[int | bool],
        value: int | float | np.ndarray | list[int | float] | tuple[int | float],
    ):
        # this is a very simple 1D buffer, no parsing required, directly set buffer
        self.buffer.data[key] = value
        self._update_range(key)

        self._emit_event("sizes", key, value)

    def __len__(self):
        return len(self.buffer.data)


class Thickness(GraphicFeature):
    """line thickness"""

    def __init__(self, value: float):
        self._value = value
        super().__init__()

    @property
    def value(self) -> float:
        return self._value

    @block_reentrance
    def set_value(self, graphic, value: float):
        graphic.world_object.material.thickness = value
        self._value = value

        event = FeatureEvent(type="thickness", info={"value": value})
        self._call_event_handlers(event)


class VertexCmap(BufferManager):
    """
    Sliceable colormap feature, manages a VertexColors instance and
    provides a way to set colormaps with arbitrary transforms
    """

    def __init__(
        self,
        vertex_colors: VertexColors,
        cmap_name: str | None,
        transform: np.ndarray | None,
        alpha: float = 1.0,
    ):
        super().__init__(data=vertex_colors.buffer)

        self._vertex_colors = vertex_colors
        self._cmap_name = cmap_name
        self._transform = transform
        self._alpha = alpha

        if self._cmap_name is not None:
            if not isinstance(self._cmap_name, str):
                raise TypeError(
                    f"cmap name must be of type <str>, you have passed: {self._cmap_name} of type: {type(self._cmap_name)}"
                )

            if self._transform is not None:
                self._transform = np.asarray(self._transform)

            n_datapoints = vertex_colors.value.shape[0]

            colors = parse_cmap_values(
                n_colors=n_datapoints,
                cmap_name=self._cmap_name,
                transform=self._transform,
            )
            colors[:, -1] = alpha
            # set vertex colors from cmap
            self._vertex_colors[:] = colors

    @block_reentrance
    def __setitem__(self, key: slice, cmap_name):
        if not isinstance(key, slice):
            raise TypeError(
                "fancy indexing not supported for VertexCmap, only slices "
                "of a continuous are supported for apply a cmap"
            )
        if key.step is not None:
            raise TypeError(
                "step sized indexing not currently supported for setting VertexCmap, "
                "slices must be a continuous region"
            )

        # parse slice
        start, stop, step = key.indices(self.value.shape[0])
        n_elements = len(range(start, stop, step))

        colors = parse_cmap_values(
            n_colors=n_elements, cmap_name=cmap_name, transform=self._transform
        )
        colors[:, -1] = self.alpha

        self._cmap_name = cmap_name
        self._vertex_colors[key] = colors

        # TODO: should we block vertex_colors from emitting an event?
        #  Because currently this will result in 2 emitted events, one
        #  for cmap and another from the colors
        self._emit_event("cmap", key, cmap_name)

    @property
    def name(self) -> str:
        return self._cmap_name

    @property
    def transform(self) -> np.ndarray | None:
        """Get or set the cmap transform. Maps values from the transform array to the cmap colors"""
        return self._transform

    @transform.setter
    def transform(
        self,
        values: np.ndarray | list[float | int],
        indices: slice | list | np.ndarray = None,
    ):
        if self._cmap_name is None:
            raise AttributeError(
                "cmap name is not set, set the cmap name before setting the transform"
            )

        values = np.asarray(values)

        colors = parse_cmap_values(
            n_colors=self.value.shape[0], cmap_name=self._cmap_name, transform=values
        )

        colors[:, -1] = self.alpha

        self._transform = values

        if indices is None:
            indices = slice(None)

        self._vertex_colors[indices] = colors

        self._emit_event("cmap.transform", indices, values)

    @property
    def alpha(self) -> float:
        """Get or set the alpha level"""
        return self._alpha

    @alpha.setter
    def alpha(self, value: float, indices: slice | list | np.ndarray = None):
        self._vertex_colors[indices, -1] = value
        self._alpha = value

        self._emit_event("cmap.alpha", indices, value)

    def __len__(self):
        raise NotImplementedError(
            "len not implemented for `cmap`, use len(colors) instead"
        )

    def __repr__(self):
        return f"{self.__class__.__name__} | cmap: {self.name}\ntransform: {self.transform}"
