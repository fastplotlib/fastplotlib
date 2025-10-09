from typing import Sequence

import numpy as np
import pygfx

from ._base import (
    GraphicFeature,
    BufferManager,
    GraphicFeatureEvent,
    to_gpu_supported_dtype,
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
    # Unicode
    "●": "circle",
    "○": "ring",
    "■": "square",
    "♦": "diamond",
    "♥": "heart",
    "♠": "spade",
    "♣": "club",
    "✳": "asterix",
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
    "✳️": "asterix",
    "📍": "pin",
}


def user_input_to_marker(name):
    resolved_name = marker_names.get(name, name).lower()
    if resolved_name not in pygfx.MarkerShape:
        raise ValueError(
            f"markers must be a string in: {list(pygfx.MarkerShape) + list(marker_names.keys())}, not {name!r}"
        )

    return resolved_name

def validate_user_markers(markers):
    # make sure all markers are valid
    # need to validate before converting to ints because
    # we can't use control flow in the vectorized function
    unique_values = np.unique(markers)
    for m in unique_values:
        user_input_to_marker(m)

# fast vectorized function to convert array of user markers to the standardized strings
vectorized_user_markers_to_std_markers = np.vectorize(marker_names.get, otypes="<U14")

# maps the human-readable marker name to the integers stored in the buffer
marker_int_mapping = dict.fromkeys(list(pygfx.MarkerShape))

# numpy vectorize to map the marker strings to ints is much faster than a for loop or python's list(map(d.get, array))
# to elaborate:
# np.vectorize(marker_int_mapping.get)(markers_str_array)
# is much faster than:
# np.asarray(list(map(marker_int_mapping.get, markers_str_array)))
# both of these are much faster than a for loop

for k in marker_int_mapping.keys():
    marker_int_mapping[k] = pygfx.MarkerInt[k]

# fast vectorized function to convert array of string markers to int
vectorized_markers_to_int = np.vectorize(marker_int_mapping.get, otypes=np.int32)


class VertexMarkers(BufferManager):
    property_name = "markers"
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

    def __init__(self, markers: str | Sequence[str] | np.ndarray):
        """
        Manages the markers buffer for the scatter points. Supports fancy indexing.
        """
        n_datapoints = len(markers)

        markers_int_array = np.zeros(n_datapoints, dtype=np.int32)
        marker_str_length = max(map(len, list(pygfx.MarkerShape)))

        self._markers_readable_array = np.empty(n_datapoints, dtype=f"<U{marker_str_length}")

        if not isinstance(markers, str):
            unique_markers = validate_user_markers(markers)
            # TODO: need to finish this

        for i, m in enumerate(markers):
            m = user_input_to_marker(m)
            self._markers_readable_array[i] = m
            markers_int_array[i] = marker_int_mapping[m]

        super().__init__(markers_int_array, isolated_buffer=False)

    @property
    def value(self) -> np.ndarray[str]:
        """numpy array of per-vertex marker shapes in human-readable form"""
        self._markers_readable_array

    @property
    def value_int(self) -> np.ndarray[np.int32]:
        """numpy array of the actual int32 buffer that represents per-vertex marker shapes on the GPU"""
        return self.buffer.data

    @block_reentrance
    def __setitem__(
        self,
        key: int | slice | np.ndarray[int | bool],
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

            if isinstance(value, str):
                # set markers at these indices to this value
                m = user_input_to_marker(value)
                self._markers_readable_array[key] = m
                self.value_int[key] = marker_int_mapping[m]

            elif isinstance(value, (np.ndarray, Sequence)):
                if n_markers != len(value):
                    raise IndexError(
                        f"Must provide one marker value, or an array/list/tuple of marker values with the same length "
                        f"as the slice. You have provided the slice: {key}, which refers to {n_markers} markers, but "
                        f"provided {len(value)} new marker values. You must provide 1 or {n_markers} values."
                    )

                # make sure all markers are valid
                # need to validate before converting to ints because
                # we can't use control flow in the vectorized function
                unique_values = np.unique(value)
                for m in unique_values:
                    user_input_to_marker(m)

                new_markers_human_readable = vectorized_user_markers_to_std_markers(value)
                new_markers_int = vectorized_markers_to_int(new_markers_human_readable)

                self._markers_readable_array[key] = new_markers_human_readable
                self.value_int[key] = new_markers_int

        elif isinstance(key, np.ndarray):
            pass

        else:
            raise TypeError

        # _update_range handles parsing the key to
        # determine offset and size for GPU upload
        self._update_range(key)

        self._emit_event("markers", key, value)

    def __len__(self):
        return len(self.buffer.data)


class UniformMarker(GraphicFeature):
    property_name = "markers"
    event_info_spec = [
        {
            "dict key": "value",
            "type": "str | None",
            "description": "new marker value",
        },
    ]

    def __init__(self, value: str | np.ndarray | tuple | list | pygfx.Color):
        """Manages uniform marker for scatter material"""

        self._value = pygfx.Color(value)
        super().__init__()

    @property
    def value(self) -> str:
        return self._value

    @block_reentrance
    def set_value(self, graphic, value: str | np.ndarray | tuple | list | pygfx.Color):
        value = pygfx.Color(value)
        graphic.world_object.material.color = value
        self._value = value

        event = GraphicFeatureEvent(type="colors", info={"value": value})
        self._call_event_handlers(event)
