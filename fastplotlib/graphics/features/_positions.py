from typing import Any, Sequence

import numpy as np
import pygfx

from ...utils import (
    parse_cmap_values,
)
from ._base import (
    GraphicFeature,
    BufferManager,
    GraphicFeatureEvent,
    to_gpu_supported_dtype,
    block_reentrance,
)
from .utils import parse_colors, is_single_color


class VertexColors(BufferManager):
    event_info_spec = [
        {
            "dict key": "key",
            "type": "slice, index, numpy-like fancy index",
            "description": "index/slice at which colors were indexed/sliced",
        },
        {
            "dict key": "value",
            "type": "np.ndarray [n_points_changed, RGBA]",
            "description": "new color values for points that were changed",
        },
        {
            "dict key": "user_value",
            "type": "str or array-like",
            "description": "user input value that was parsed into the RGBA array",
        },
    ]

    def __init__(
        self,
        colors: str | pygfx.Color | np.ndarray | Sequence[float] | Sequence[str],
        n_colors: int,
        property_name: str = "colors",
    ):
        """
        Manages the vertex color buffer for :class:`LineGraphic` or :class:`ScatterGraphic`

        Parameters
        ----------
        colors: str | pygfx.Color | np.ndarray | Sequence[float] | Sequence[str]
            specify colors as a single human-readable string, RGBA array,
            or an iterable of strings or RGBA arrays

        n_colors: int
            number of colors, if passing in a single str or single RGBA array

        """
        data = parse_colors(colors, n_colors)

        super().__init__(data=data, property_name=property_name)

    def set_value(
        self,
        graphic,
        value: str | pygfx.Color | np.ndarray | Sequence[float] | Sequence[str],
    ):
        """set the entire array, create new buffer if necessary"""
        # a sequence of colors whose length differs from the current buffer requires a new buffer
        if (
            isinstance(value, (np.ndarray, list, tuple))
            and not is_single_color(value)
            and self.buffer.data.shape[0] != len(value)
        ):
            # parse the new colors
            new_colors = parse_colors(value, len(value))

            # create the new buffer, old buffer should get dereferenced
            # make sure new buffer is isolated (i.e. allocate a buffer, then set the values)
            buff = np.empty(new_colors.shape, dtype=np.float32)
            buff[:] = new_colors
            self._fpl_buffer = pygfx.Buffer(buff)
            graphic.world_object.geometry.colors = self._fpl_buffer

            if len(self._event_handlers) < 1:
                return

            event_info = {
                "key": slice(None),
                "value": new_colors,
                "user_value": value,
            }

            event = GraphicFeatureEvent(self._property_name, info=event_info)
            self._call_event_handlers(event)
            return

        self[:] = value

    @block_reentrance
    def __setitem__(
        self,
        key: int | slice | np.ndarray[int | bool] | tuple[slice, ...],
        user_value: str | pygfx.Color | np.ndarray | Sequence[float] | Sequence[str],
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

        event = GraphicFeatureEvent(self._property_name, info=event_info)
        self._call_event_handlers(event)

    def __len__(self):
        return len(self.buffer.data)


class UniformColor(GraphicFeature):
    event_info_spec = [
        {
            "dict key": "value",
            "type": "str | pygfx.Color | np.ndarray | Sequence[float]",
            "description": "new color value",
        },
    ]

    def __init__(
        self,
        value: str | pygfx.Color | np.ndarray | Sequence[float],
        property_name: str = "colors",
    ):
        """Manages uniform color for line or scatter material"""

        self._value = pygfx.Color(value)
        super().__init__(property_name=property_name)

    @property
    def value(self) -> pygfx.Color:
        return self._value

    @block_reentrance
    def set_value(
        self, graphic, value: str | pygfx.Color | np.ndarray | Sequence[float]
    ):
        value = pygfx.Color(value)
        graphic.world_object.material.color = value
        self._value = value

        event = GraphicFeatureEvent(type=self._property_name, info={"value": value})
        self._call_event_handlers(event)


class SizeSpace(GraphicFeature):
    event_info_spec = [
        {
            "dict key": "value",
            "type": "str",
            "description": "'screen' | 'world' | 'model'",
        },
    ]

    def __init__(self, value: str, property_name: str = "size_space"):
        """Manages the coordinate space for scatter/line graphic"""

        self._value = value
        super().__init__(property_name=property_name)

    @property
    def value(self) -> str:
        return self._value

    @block_reentrance
    def set_value(self, graphic, value: str):
        if value not in ["screen", "world", "model"]:
            raise ValueError(
                f"`size_space` must be one of: {['screen', 'world', 'model']}"
            )

        if "Line" in graphic.world_object.material.__class__.__name__:
            graphic.world_object.material.thickness_space = value
        else:
            graphic.world_object.material.size_space = value
        self._value = value

        event = GraphicFeatureEvent(type=self._property_name, info={"value": value})
        self._call_event_handlers(event)


class VertexPositions(BufferManager):
    event_info_spec = [
        {
            "dict key": "key",
            "type": "slice, index (int) or numpy-like fancy index",
            "description": "key at which vertex positions data were indexed/sliced",
        },
        {
            "dict key": "value",
            "type": "int | float | array-like",
            "description": "new data values for points that were changed",
        },
    ]

    def __init__(self, data: Any, property_name: str = "data"):
        """
        Manages the vertex positions buffer shown in the graphic.
        Supports fancy indexing if the data array also supports it.
        """

        data = self._fix_data(data)
        super().__init__(data, property_name=property_name)

    def _fix_data(self, data):
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

    def set_value(self, graphic, value):
        """Sets the entire array, creates new buffer if necessary"""
        if isinstance(value, np.ndarray):
            if self.buffer.data.shape[0] != value.shape[0]:
                # number of items doesn't match, create a new buffer

                # if data is not 3D
                if value.ndim == 1:
                    # _fix_data creates a new array so we don't need to re-allocate with np.zeros
                    bdata = self._fix_data(value)

                elif value.shape[1] == 2:
                    # _fix_data creates a new array so we don't need to re-allocate with np.zeros
                    bdata = self._fix_data(value)

                elif value.shape[1] == 3:
                    # need to allocate a buffer to use here
                    bdata = np.empty(value.shape, dtype=np.float32)
                    bdata[:] = value[:]

                # create the new buffer, old buffer should get dereferenced
                self._fpl_buffer = pygfx.Buffer(bdata)
                graphic.world_object.geometry.positions = self._fpl_buffer

                self._emit_event(self._property_name, key=slice(None), value=value)
                return

        self[:] = value

    @block_reentrance
    def __setitem__(
        self,
        key: int | slice | np.ndarray[int | bool] | tuple[slice, ...],
        value: np.ndarray | float | list[float],
    ):
        # directly use the key to slice the buffer and set the values
        self.buffer.data[key] = value

        # _update_range handles parsing the key to
        # determine offset and size for GPU upload
        self._update_range(key)

        self._emit_event(self._property_name, key, value)

    def __len__(self):
        return len(self.buffer.data)


class VertexCmap(BufferManager):
    event_info_spec = [
        {
            "dict key": "key",
            "type": "slice",
            "description": "key at cmap colors were sliced",
        },
        {
            "dict key": "value",
            "type": "str",
            "description": "new cmap to set at given slice",
        },
    ]

    def __init__(
        self,
        vertex_colors: VertexColors,
        cmap_name: str | None,
        transform: np.ndarray | None,
        property_name: str = "colors",
    ):
        """
        Sliceable colormap feature, manages a VertexColors instance and
        provides a way to set colormaps with arbitrary transforms
        """

        super().__init__(data=None, property_name=property_name)

        self._vertex_colors = vertex_colors
        self._cmap_name = cmap_name
        self._transform = transform

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
            # set vertex colors from cmap
            self._vertex_colors[:] = colors

    @property
    def buffer(self) -> pygfx.Buffer:
        return self._vertex_colors.buffer

    @property
    def value(self) -> np.ndarray:
        # mirror the managed colors feature, whose length is the number of color entries
        # (this is per-line, not per-vertex, for an InfLineColors)
        return self._vertex_colors.value

    @block_reentrance
    def __setitem__(self, key: slice, cmap_name):
        if not isinstance(key, slice):
            raise TypeError(
                "fancy indexing not supported for VertexCmap, only slices "
                "of a continuous range are supported for applying a cmap"
            )
        if key.step is not None:
            raise TypeError(
                "step sized indexing not currently supported for setting VertexCmap, "
                "slices must be a continuous range"
            )

        # parse slice
        start, stop, step = key.indices(self.value.shape[0])
        n_elements = len(range(start, stop, step))

        colors = parse_cmap_values(
            n_colors=n_elements, cmap_name=cmap_name, transform=self._transform
        )

        self._cmap_name = cmap_name
        self._vertex_colors[key] = colors

        # TODO: should we block vertex_colors from emitting an event?
        #  Because currently this will result in 2 emitted events, one
        #  for cmap and another from the colors
        self._emit_event(self._property_name, key, cmap_name)

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

        self._transform = values

        if indices is None:
            indices = slice(None)

        self._vertex_colors[indices] = colors

        self._emit_event("cmap.transform", indices, values)

    def __len__(self):
        raise NotImplementedError(
            "len not implemented for `cmap`, use len(colors) instead"
        )

    def __repr__(self):
        return f"{self.__class__.__name__} | cmap: {self.name}\ntransform: {self.transform}"


class InfLineAxisData(VertexPositions):
    """
    Manages the positions buffer for :class:`InfLineGraphic`.

    Each infinite line is stored as a two-point segment, so the buffer has two vertices per
    line. When ``axis`` is one of ``"x", "y", "z"`` the data is a 1D array of positions along
    that axis and one infinite line is drawn at each position. When ``axis`` is ``None`` the
    data is used directly as the segment endpoints (2 points per line).

    Indexing and ``value`` operate per-line: ``value`` is a 1D array of ``n_lines`` axis
    positions, or an ``[n_lines, 2, 3]`` array of segment endpoints when ``axis`` is ``None``.
    """

    _AXIS_INDICES = {"x": 0, "y": 1, "z": 2}

    def __init__(self, data: Any, axis: str | None = None, property_name: str = "data"):
        if axis is not None and axis not in self._AXIS_INDICES:
            raise ValueError(
                f"`axis` must be one of 'x', 'y', 'z', or None, you have passed: {axis!r}"
            )
        self._axis = axis
        super().__init__(data, property_name=property_name)

    @property
    def axis(self) -> str | None:
        return self._axis

    def _fix_data(self, data):
        data = np.asarray(data)

        if self._axis is None:
            # data is used directly as the segment endpoints, 2 points per line;
            # accept the grouped [n_lines, 2, 3] form as well as a flat [n_points, 3] buffer
            if data.ndim == 3:
                data = data.reshape(-1, data.shape[-1])
            data = super()._fix_data(data)
            if data.shape[0] % 2 != 0:
                raise ValueError(
                    "when `axis` is None, `data` is used directly as the infinite line segment "
                    "endpoints and must contain an even number of points (2 per line)"
                )
            return data

        # axis is 'x', 'y', or 'z': `data` is a 1D array of positions along that axis
        if data.ndim != 1:
            raise ValueError(
                f"when `axis` is '{self._axis}', `data` must be a 1D array of positions along that "
                f"axis, you have passed an array with {data.ndim} dimensions"
            )

        axis_index = self._AXIS_INDICES[self._axis]
        # the two points of a line share the axis position; they differ along another axis
        # so the segment has a direction along which it is extended to infinity
        run_index = 1 if axis_index == 0 else 0

        buffer = np.zeros((2 * data.size, 3), dtype=np.float32)
        buffer[:, axis_index] = np.repeat(data, 2)
        buffer[1::2, run_index] = 1.0

        return buffer

    def __len__(self) -> int:
        return len(self.buffer.data) // 2

    @property
    def value(self) -> np.ndarray:
        if self._axis is None:
            # one [2, 3] pair of endpoints per line
            return self.buffer.data.reshape(len(self), 2, 3)
        # both endpoints of a line share the axis position, return one value per line
        return self.buffer.data[::2, self._AXIS_INDICES[self._axis]]

    def __getitem__(self, key):
        return self.value[key]

    def set_value(self, graphic, value):
        """set the line positions, allocating a new buffer if the number of lines changed"""
        value = np.asarray(value)

        if self._axis is None:
            fixed = self._fix_data(value)
            if fixed.shape[0] != len(self.buffer.data):
                # number of lines changed, allocate a new buffer
                self._fpl_buffer = pygfx.Buffer(fixed)
                graphic.world_object.geometry.positions = self._fpl_buffer
                # emit the [n_lines, 2, 3] form to match `value` and the in-place path
                self._emit_event(
                    self._property_name, slice(None), fixed.reshape(-1, 2, 3)
                )
                return
            self[:] = fixed.reshape(len(self), 2, 3)
            return

        if value.ndim != 1:
            raise ValueError(
                f"when `axis` is '{self._axis}', data must be set with a 1D array of axis positions"
            )
        if value.size != len(self):
            # number of lines changed, allocate a new buffer
            self._fpl_buffer = pygfx.Buffer(self._fix_data(value))
            graphic.world_object.geometry.positions = self._fpl_buffer
            self._emit_event(self._property_name, slice(None), value)
            return

        self[:] = value

    @block_reentrance
    def __setitem__(self, key, value):
        # for axis=None, `value` is [n_lines, 2, 3] so the line index is the first
        # element of a multi-dimensional endpoint/coordinate key
        line_key = key[0] if (self._axis is None and isinstance(key, tuple)) else key
        line_indices = np.atleast_1d(np.arange(len(self))[line_key])
        if line_indices.size == 0:
            return

        if self._axis is None:
            self.buffer.data.reshape(len(self), 2, 3)[key] = value
        else:
            axis_index = self._AXIS_INDICES[self._axis]
            # write the axis position to both endpoints of each line
            self.buffer.data[2 * line_indices, axis_index] = value
            self.buffer.data[2 * line_indices + 1, axis_index] = value

        offset = 2 * int(line_indices.min())
        size = 2 * (int(line_indices.max()) - int(line_indices.min()) + 1)
        self.buffer.update_range(offset=offset, size=size)

        self._emit_event(self._property_name, key, value)


class InfLineColors(VertexColors):
    """
    Manages per-line colors for :class:`InfLineGraphic`.

    One color is stored per infinite line; internally each color is written to both
    endpoints of the line's segment so that the segment renders as a single solid color.
    """

    def __init__(self, colors, n_colors: int, property_name: str = "colors"):
        # n_colors is the number of infinite lines; each line spans two vertices
        data = np.repeat(parse_colors(colors, n_colors), 2, axis=0)
        # bypass VertexColors.__init__, which would parse the (already parsed) colors again
        BufferManager.__init__(self, data=data, property_name=property_name)

    @property
    def value(self) -> np.ndarray:
        # both vertices of a line share its color, return one color per line
        return self.buffer.data[::2]

    def __getitem__(self, key):
        return self.value[key]

    def __len__(self) -> int:
        return len(self.buffer.data) // 2

    def set_value(self, graphic, value):
        """set the per-line colors, allocating a new buffer if the number of lines changed"""
        if not is_single_color(value) and len(value) != len(self):
            data = np.repeat(parse_colors(value, len(value)), 2, axis=0)
            buff = np.empty(data.shape, dtype=np.float32)
            buff[:] = data
            self._fpl_buffer = pygfx.Buffer(buff)
            graphic.world_object.geometry.colors = self._fpl_buffer

            if len(self._event_handlers) < 1:
                return

            event_info = {"key": slice(None), "value": data, "user_value": value}
            event = GraphicFeatureEvent(self._property_name, info=event_info)
            self._call_event_handlers(event)
            return

        self[:] = value

    @block_reentrance
    def __setitem__(self, key, value):
        # the line index is the first element of a multi-dimensional (per-channel) key
        line_key = key[0] if isinstance(key, tuple) else key
        line_indices = np.atleast_1d(np.arange(len(self))[line_key])
        if line_indices.size == 0:
            return

        if isinstance(key, tuple):
            # channel-level write, e.g. colors[i, :3]; set the value directly, no color parsing
            colors = value
            rest = key[1:]
            self.buffer.data[(2 * line_indices, *rest)] = value
            self.buffer.data[(2 * line_indices + 1, *rest)] = value
        else:
            # one color per selected line, written to both of the line's vertices
            colors = parse_colors(value, line_indices.size)
            self.buffer.data[2 * line_indices] = colors
            self.buffer.data[2 * line_indices + 1] = colors

        offset = 2 * int(line_indices.min())
        size = 2 * (int(line_indices.max()) - int(line_indices.min()) + 1)
        self.buffer.update_range(offset=offset, size=size)

        if len(self._event_handlers) < 1:
            return

        event_info = {"key": key, "value": colors, "user_value": value}
        event = GraphicFeatureEvent(self._property_name, info=event_info)
        self._call_event_handlers(event)
