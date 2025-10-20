from typing import Sequence

import numpy as np
import pygfx

from ._base import (
    GraphicFeature,
    BufferManager,
    GraphicFeatureEvent,
    block_reentrance,
)


marker_names = {
    # MPL
    "o": "circle",
    "s": "square",
    "D": "diamond",
    "+": "plus",
    "x": "cross",
    "^": "triangle_up",
    "<": "triangle_left",
    ">": "triangle_right",
    "v": "triangle_down",
    "*": "asterisk6",
    # Unicode
    "●": "circle",
    "○": "ring",
    "■": "square",
    "♦": "diamond",
    "♥": "heart",
    "♠": "spade",
    "♣": "club",
    "✳": "asterisk6",
    "▲": "triangle_up",
    "▼": "triangle_down",
    "◀": "triangle_left",
    "▶": "triangle_right",
    # Emojis (these may look like their plaintext variants in your editor)
    "❤️": "heart",
    "♠️": "spade",
    "♣️": "club",
    "♦️": "diamond",
    "💎": "diamond",
    "💍": "ring",
    "✳️": "asterisk6",
    "📍": "pin",
}


def user_input_to_marker(name):
    resolved_name = marker_names.get(name, name).lower()
    if resolved_name not in pygfx.MarkerShape:
        raise ValueError(
            f"markers must be a string in: {list(pygfx.MarkerShape) + list(marker_names.keys())}, not {name!r}"
        )

    return resolved_name

def validate_user_markers_array(markers):
    # make sure all markers are valid
    # need to validate before converting to ints because
    # we can't use control flow in the vectorized function
    unique_values = np.unique(markers)
    for m in unique_values:
        user_input_to_marker(m)

# fast vectorized function to convert array of user markers to the standardized strings
# TODO: can probably use search-sorted for this too
vectorized_user_markers_to_std_markers = np.vectorize(marker_names.get, otypes=["<U14"])

# maps the human-readable marker name to the integers stored in the buffer
marker_int_mapping = dict(pygfx.MarkerInt.__members__)

# search sorted is the fastest way to map an array of str -> array of int
# see: https://github.com/pygfx/pygfx/issues/1215
# Prepare for searchsorted
def init_searchsorted(markers_mapping):
    keys = np.array(list(markers_mapping.keys()))
    vals = np.array(list(markers_mapping.values()))

    order = np.argsort(keys)
    keys = keys[order]
    vals = vals[order]

    return keys, vals

marker_int_searchsorted_keys, marker_int_searchsorted_vals = init_searchsorted(marker_int_mapping)


def searchsorted_markers_to_int_array(markers_str_array: np.ndarray[str]):
    # Vectorized lookup
    indices = np.searchsorted(marker_int_searchsorted_keys, markers_str_array)
    return marker_int_searchsorted_vals[indices]


class VertexMarkers(BufferManager):
    event_info_spec = [
        {
            "dict key": "key",
            "type": "slice, index (int) or numpy-like fancy index",
            "description": "key at which markers were indexed/sliced",
        },
        {
            "dict key": "value",
            "type": "str | np.ndarray[str]",
            "description": "new marker values for points that were changed",
        },
    ]

    def __init__(self, markers: str | Sequence[str] | np.ndarray, n_datapoints: int, property_name: str = "markers"):
        """
        Manages the markers buffer for the scatter points. Supports fancy indexing.
        """

        # first validate then allocate buffers

        if isinstance(markers, str):
            markers = user_input_to_marker(markers)

        elif isinstance(markers, (tuple, list, np.ndarray)):
            validate_user_markers_array(markers)

        # allocate buffers
        markers_int_array = np.zeros(n_datapoints, dtype=np.int32)

        marker_str_length = max(map(len, list(pygfx.MarkerShape)))

        self._markers_readable_array = np.empty(n_datapoints, dtype=f"<U{marker_str_length}")

        if isinstance(markers, str):
            # all markers in the array are identical, so set the entire array
            self._markers_readable_array[:] = markers
            markers_int_array[:] = marker_int_mapping[markers]

        elif isinstance(markers, (np.ndarray, tuple, list)):
            # distinct marker for each point
            # first vectorized map from user marker strings to "standard" marker strings
            self._markers_readable_array = vectorized_user_markers_to_std_markers(markers)
            # map standard marker strings to integer array
            markers_int_array[:] = searchsorted_markers_to_int_array(self._markers_readable_array)

        super().__init__(markers_int_array, isolated_buffer=False, property_name=property_name)

    @property
    def value(self) -> np.ndarray[str]:
        """numpy array of per-vertex marker shapes in human-readable form"""
        return self._markers_readable_array

    @property
    def value_int(self) -> np.ndarray[np.int32]:
        """numpy array of the actual int32 buffer that represents per-vertex marker shapes on the GPU"""
        return self.buffer.data

    def _set_markers_arrays(self, key, value, n_markers):
        if isinstance(value, str):
            # set markers at these indices to this value
            m = user_input_to_marker(value)
            self._markers_readable_array[key] = m
            self.value_int[key] = marker_int_mapping[m]

        elif isinstance(value, (np.ndarray, list, tuple)):
            if n_markers != len(value):
                raise IndexError(
                    f"Must provide one marker value, or an array/list/tuple of marker values with the same length "
                    f"as the slice. You have provided the slice: {key}, which refers to {n_markers} markers, but "
                    f"provided {len(value)} new marker values. You must provide 1 or {n_markers} values."
                )

            validate_user_markers_array(value)

            new_markers_human_readable = vectorized_user_markers_to_std_markers(value)
            new_markers_int = searchsorted_markers_to_int_array(new_markers_human_readable)

            self._markers_readable_array[key] = new_markers_human_readable
            self.value_int[key] = new_markers_int
        else:
            raise TypeError(
                "new markers value must be a str, Sequence or np.ndarray of new marker values"
            )

    @block_reentrance
    def __setitem__(
        self,
        key: int | slice | list[int | bool] | np.ndarray[int | bool],
        value: str | Sequence[str] | np.ndarray[str],
    ):
        if isinstance(key, int):
            if key >= self.value.size:
                raise IndexError(f"index : {key} out of bounds: {self.value.size}")

            if not isinstance(value, str):
                # only a single marker should be provided if changing one at one index
                raise TypeError(
                    f"you must provide a <str> marker value if providing a single <int> index, "
                    f"you have passed index: {key} and value: {value}"
                )

            m = user_input_to_marker(value)
            self._markers_readable_array[key] = m
            self.value_int[key] = marker_int_mapping[m]

        elif isinstance(key, slice):
            # find the number of new markers by converting slice to range and then parse markers
            start, stop, step = key.indices(self.value.size)

            n_markers = len(range(start, stop, step))
            self._set_markers_arrays(key, value, n_markers)

        elif isinstance(key, (list, np.ndarray)):
            key = np.asarray(key)  # convert to array if list

            if key.dtype == bool:
                # make sure len is same
                if not key.size == self.buffer.data.shape[0]:
                    raise IndexError(
                        f"Length of array for fancy indexing must match number of datapoints.\n"
                        f"There are {len(self.buffer.data.shape[0])} datapoints and you have passed "
                        f"a bool array of size: {key.size}"
                    )

                n_markers = np.count_nonzero(key)
                self._set_markers_arrays(key, value, n_markers)

            # if it's an array of int
            elif np.issubdtype(key.dtype, np.integer):
                if key.size > self.buffer.data.shape[0]:
                    raise IndexError(
                        f"Length of array for fancy indexing must be <= n_datapoints. "
                        f"There are: {self.buffer.data.shape[0]} datapoints, you have passed an "
                        f"integer array for fancy indexing of size: {key.size}"
                    )
                n_markers = key.size
                self._set_markers_arrays(key, value, n_markers)

            else:
                # fancy indexing doesn't make sense with non-integer types
                raise TypeError(
                    f"can only using integer or booleans arrays for fancy indexing, your array is of type: {key.dtype}"
                )

        else:
            raise TypeError(
                f"Can only set markers by slicing/indexing using the one of the following types: "
                f"int | slice | list[int | bool] | np.ndarray[int | bool], you have passed"
                f"sliced using the following type: {type(key)}"
            )

        # _update_range handles parsing the key to
        # determine offset and size for GPU upload
        self._update_range(key)

        self._emit_event(self._property_name, key, value)

    def __len__(self):
        return len(self.buffer.data)


class UniformMarker(GraphicFeature):
    event_info_spec = [
        {
            "dict key": "value",
            "type": "str | None",
            "description": "new marker value",
        },
    ]

    def __init__(self, marker: str, property_name: str = "markers"):
        """Manages evented uniform buffer for scatter marker"""

        self._value = user_input_to_marker(marker)
        super().__init__(property_name=property_name)

    @property
    def value(self) -> str:
        return self._value

    @block_reentrance
    def set_value(self, graphic, value: str):
        value = user_input_to_marker(value)
        graphic.world_object.material.marker = value
        self._value = value

        event = GraphicFeatureEvent(type=self._property_name, info={"value": value})
        self._call_event_handlers(event)


class UniformEdgeColor(GraphicFeature):
    event_info_spec = [
        {
            "dict key": "value",
            "type": "str | np.ndarray | pygfx.Color | Sequence[float]",
            "description": "new edge_color",
        },
    ]

    def __init__(self, edge_color: str | np.ndarray | pygfx.Color | Sequence[float], property_name: str = "edge_colors"):
        """Manages evented uniform buffer for scatter marker edge_color"""

        self._value = pygfx.Color(edge_color)
        super().__init__(property_name=property_name)

    @property
    def value(self) -> pygfx.Color:
        return self._value

    @block_reentrance
    def set_value(self, graphic, value: str | np.ndarray | pygfx.Color | Sequence[float]):
        graphic.world_object.material.edge_color = pygfx.Color(value)
        self._value = value

        event = GraphicFeatureEvent(type=self._property_name, info={"value": value})
        self._call_event_handlers(event)


class EdgeWidth(GraphicFeature):
    event_info_spec = [
        {
            "dict key": "value",
            "type": "float",
            "description": "new edge_width",
        },
    ]

    def __init__(self, edge_width: float, property_name: str = "edge_width"):
        """Manages evented uniform buffer for scatter marker edge_width"""

        self._value = edge_width
        super().__init__(property_name=property_name)

    @property
    def value(self) -> float:
        return self._value

    @block_reentrance
    def set_value(self, graphic, value: float):
        graphic.world_object.material.edge_width = value
        self._value = value

        event = GraphicFeatureEvent(type=self._property_name, info={"value": value})
        self._call_event_handlers(event)


class UniformRotations(GraphicFeature):
    event_info_spec = [
        {
            "dict key": "value",
            "type": "float",
            "description": "new edge_width",
        },
    ]

    def __init__(self, edge_width: float, property_name: str = "point_rotations"):
        """Manages evented uniform buffer for scatter marker rotation"""

        self._value = edge_width
        super().__init__(property_name=property_name)

    @property
    def value(self) -> float:
        return self._value

    @block_reentrance
    def set_value(self, graphic, value: float):
        graphic.world_object.material.rotations = value
        self._value = value

        event = GraphicFeatureEvent(type=self._property_name, info={"value": value})
        self._call_event_handlers(event)


class VertexRotations(BufferManager):
    event_info_spec = [
        {
            "dict key": "key",
            "type": "slice, index (int) or numpy-like fancy index",
            "description": "key at which point rotations were indexed/sliced",
        },
        {
            "dict key": "value",
            "type": "int | float | array-like",
            "description": "new rotation values for points that were changed",
        },
    ]

    def __init__(
        self,
        rotations: int | float | np.ndarray | Sequence[int | float],
        n_datapoints: int,
        isolated_buffer: bool = True,
        property_name: str = "point_rotations"
    ):
        """
        Manages rotations buffer of scatter points.
        """
        sizes = self._fix_sizes(rotations, n_datapoints)
        super().__init__(data=sizes, isolated_buffer=isolated_buffer, property_name=property_name)

    def _fix_sizes(
        self,
        sizes: int | float | np.ndarray | Sequence[int | float],
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
                    f"sequence of `rotations` must be 1 dimensional with "
                    f"the same length as the number of datapoints"
                )

        else:
            raise TypeError(
                "`rotations` must be a single <int>, <float>, or a sequence (array, list, tuple) of int"
                "or float with the length equal to the number of datapoints"
            )

        return sizes

    @block_reentrance
    def __setitem__(
        self,
        key: int | slice | np.ndarray[int | bool] | list[int | bool],
        value: int | float | np.ndarray | Sequence[int | float],
    ):
        # this is a very simple 1D buffer, no parsing required, directly set buffer
        self.buffer.data[key] = value
        self._update_range(key)

        self._emit_event(self._property_name, key, value)

    def __len__(self):
        return len(self.buffer.data)


class VertexPointSizes(BufferManager):
    event_info_spec = [
        {
            "dict key": "key",
            "type": "slice, index (int) or numpy-like fancy index",
            "description": "key at which point sizes were indexed/sliced",
        },
        {
            "dict key": "value",
            "type": "int | float | array-like",
            "description": "new size values for points that were changed",
        },
    ]

    def __init__(
        self,
        sizes: int | float | np.ndarray | Sequence[int | float],
        n_datapoints: int,
        isolated_buffer: bool = True,
        property_name: str = "sizes"
    ):
        """
        Manages sizes buffer of scatter points.
        """
        sizes = self._fix_sizes(sizes, n_datapoints)
        super().__init__(data=sizes, isolated_buffer=isolated_buffer, property_name=property_name)

    def _fix_sizes(
        self,
        sizes: int | float | np.ndarray | Sequence[int | float],
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
        value: int | float | np.ndarray | Sequence[int | float],
    ):
        # this is a very simple 1D buffer, no parsing required, directly set buffer
        self.buffer.data[key] = value
        self._update_range(key)

        self._emit_event(self._property_name, key, value)

    def __len__(self):
        return len(self.buffer.data)


class UniformSize(GraphicFeature):
    event_info_spec = [
        {"dict key": "value", "type": "float", "description": "new size value"},
    ]

    def __init__(self, value: int | float, property_name: str = "sizes"):
        """Manages uniform size for scatter material"""

        self._value = float(value)
        super().__init__(property_name=property_name)

    @property
    def value(self) -> float:
        return self._value

    @block_reentrance
    def set_value(self, graphic, value: float | int):
        value = float(value)
        graphic.world_object.material.size = value
        self._value = value

        event = GraphicFeatureEvent(type=self._property_name, info={"value": value})
        self._call_event_handlers(event)
