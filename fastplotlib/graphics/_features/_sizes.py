import numpy as np

from ._base import (
    BufferManager,
    FeatureEvent,
    to_gpu_supported_dtype,
)


class PointsSizesFeature(BufferManager):
    """
    Access to the vertex buffer data shown in the graphic.
    Supports fancy indexing if the data array also supports it.
    """

    def __init__(
            self,
            sizes: np.ndarray | list[int | float] | tuple[int | float],
            n_datapoints: int,
            isolated_buffer: bool = True
    ):
        sizes = self._fix_sizes(sizes, n_datapoints)
        super().__init__(data=sizes, isolated_buffer=isolated_buffer)

    def _fix_sizes(self, sizes: int | float | np.ndarray | list[int | float] | tuple[int | float], n_datapoints: int):
        if np.issubdtype(type(sizes), np.integer):
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

        # avoid creating dicts constantly if there are no events to handle
        if len(self._event_handlers) > 0:
            self._feature_changed(key, value)

    def _feature_changed(self, key, new_data):
        if key is not None:
            key = cleanup_slice(key, self._upper_bound)
        if isinstance(key, (int, np.integer)):
            indices = [key]
        elif isinstance(key, slice):
            indices = range(key.start, key.stop, key.step)
        elif isinstance(key, np.ndarray):
            indices = key
        elif key is None:
            indices = None

        pick_info = {
            "index": indices,
            "collection-index": self._collection_index,
            "world_object": self._parent.world_object,
            "new_data": new_data,
        }

        event_data = FeatureEvent(type="sizes", pick_info=pick_info)

        self._call_event_handlers(event_data)
