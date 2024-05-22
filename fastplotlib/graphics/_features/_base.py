from abc import abstractmethod
from inspect import getfullargspec
from warnings import warn
from typing import Any, Literal

import numpy as np
from numpy.typing import NDArray

from wgpu.gui.base import log_exception

import pygfx


supported_dtypes = [
    np.uint8,
    np.uint16,
    np.uint32,
    np.int8,
    np.int16,
    np.int32,
    np.float16,
    np.float32,
]


def to_gpu_supported_dtype(array):
    """
    If ``array`` is a numpy array, converts it to a supported type. GPUs don't support 64 bit dtypes.
    """
    if isinstance(array, np.ndarray):
        if array.dtype not in supported_dtypes:
            if np.issubdtype(array.dtype, np.integer):
                warn(f"converting {array.dtype} array to int32")
                return array.astype(np.int32)
            elif np.issubdtype(array.dtype, np.floating):
                warn(f"converting {array.dtype} array to float32")
                return array.astype(np.float32, copy=False)
            else:
                raise TypeError(
                    "Unsupported type, supported array types must be int or float dtypes"
                )

    return array


class FeatureEvent(pygfx.Event):
    """
    Dataclass that holds feature event information. Has ``type`` and ``pick_info`` attributes.

    Attributes
    ----------
    type: str, example "colors"

    pick_info: dict:

        ============== =============================================================================
        key             value
        ============== =============================================================================
        "index"         indices where feature data was changed, ``range`` object or ``List[int]``
        "world_object"  world object the feature belongs to
        "new_data:      the new data for this feature
        ============== =============================================================================

        .. note::
            pick info varies between features, this is just the general structure

    """

    def __init__(self, type: str, info: dict):
        super().__init__(type=type)
        self.info = info


class GraphicFeature:
    def __init__(self, **kwargs):
        self._event_handlers = list()
        self._block_events = False

    @property
    def value(self) -> Any:
        raise NotImplemented

    def set_value(self, graphic, value: float):
        raise NotImplementedError

    def block_events(self, val: bool):
        """
        Block all events from this feature

        Parameters
        ----------
        val: bool
            ``True`` or ``False``

        """
        self._block_events = val

    def add_event_handler(self, handler: callable):
        """
        Add an event handler. All added event handlers are called when this feature changes.

        The ``handler`` can optionally accept a :class:`.FeatureEvent` as the first and only argument.
        The ``FeatureEvent`` only has 2 attributes, ``type`` which denotes the type of event
        as a ``str`` in the form of "<feature_name>", such as "color". And ``pick_info`` which contains
        information about the event and Graphic that triggered it.

        Parameters
        ----------
        handler: callable
            a function to call when this feature changes

        """
        if not callable(handler):
            raise TypeError("event handler must be callable")

        if handler in self._event_handlers:
            warn(f"Event handler {handler} is already registered.")
            return

        self._event_handlers.append(handler)

    def remove_event_handler(self, handler: callable):
        """
        Remove a registered event ``handler``.

        Parameters
        ----------
        handler: callable
            event handler to remove

        """
        if handler not in self._event_handlers:
            raise KeyError(f"event handler {handler} not registered.")

        self._event_handlers.remove(handler)

    def clear_event_handlers(self):
        """Clear all event handlers"""
        self._event_handlers.clear()

    def _call_event_handlers(self, event_data: FeatureEvent):
        if self._block_events:
            return

        for func in self._event_handlers:
            with log_exception(f"Error during handling {self.__class__.__name__} event"):
                func(event_data)

    def __repr__(self) -> str:
        raise NotImplementedError


class BufferManager(GraphicFeature):
    """Smaller wrapper for pygfx.Buffer"""

    def __init__(
            self,
            data: NDArray,
            buffer_type: Literal["buffer", "texture"] = "buffer",
            isolated_buffer: bool = True,
            texture_dim: int = 2,
            **kwargs
    ):
        super().__init__()
        if isolated_buffer:
            # useful if data is read-only, example: memmaps
            bdata = np.zeros(data.shape, dtype=data.dtype)
            bdata[:] = data[:]
        else:
            # user's input array is used as the buffer
            bdata = data

        if buffer_type == "buffer":
            self._buffer = pygfx.Buffer(bdata)
        elif buffer_type == "texture":
            self._buffer = pygfx.Texture(bdata, dim=texture_dim)
        else:
            raise ValueError("`buffer_type` must be one of: 'buffer' or 'texture'")

        self._event_handlers: list[callable] = list()

        self._shared: int = 0

    @property
    def value(self) -> NDArray:
        return self.buffer.data

    def set_value(self, graphic, value):
        """Sets values on entire array"""
        self[:] = value

    @property
    def buffer(self) -> pygfx.Buffer | pygfx.Texture:
        return self._buffer

    @property
    def shared(self) -> int:
        """Number of graphics that share this buffer"""
        return self._shared

    def __getitem__(self, item):
        return self.buffer.data[item]

    def __setitem__(self, key, value):
        raise NotImplementedError

    def _update_range(self, key: int | slice | np.ndarray[int | bool] | list[bool | int] | tuple[slice, ...]):
        """
        Uses key from slicing to determine the offset and
        size of the buffer to mark for upload to the GPU
        """
        # number of elements in the buffer
        upper_bound = self.value.shape[0]

        if isinstance(key, tuple):
            # if multiple dims are sliced, we only need the key for
            # the first dimension corresponding to n_datapoints
            key: int | np.ndarray[int | bool] | slice = key[0]

        if isinstance(key, int):
            # simplest case
            offset = key
            size = 1

        elif isinstance(key, slice):
            # parse slice
            start, stop, step = key.indices(upper_bound)

            # account for backwards indexing
            if (start > stop) and step < 0:
                offset = stop
            else:
                offset = start

            # slice.indices will give -1 if None is passed
            # which just means 0 here since buffers do not
            # use negative indexing
            offset = max(0, offset)

            # number of elements to upload
            # this is indexing so do not add 1
            size = abs(stop - start)

        elif isinstance(key, (np.ndarray, list)):
            if isinstance(key, list):
                # convert to array
                key = np.array(key)

            if not key.ndim == 1:
                raise TypeError(key)

            if key.dtype == bool:
                # convert bool mask to integer indices
                key = np.nonzero(key)[0]

            if not np.issubdtype(key.dtype, np.integer):
                # fancy indexing doesn't make sense with non-integer types
                raise TypeError(key)

            if key.size < 1:
                # nothing to update
                return

            # convert any negative integer indices to positive indices
            key %= upper_bound

            # index of first element to upload
            offset = key.min()

            # number of elements to upload
            # add 1 because this is direct
            # passing of indices, not a start:stop
            size = np.ptp(key) + 1

        else:
            raise TypeError(key)

        self.buffer.update_range(offset=offset, size=size)

    def _emit_event(self, type: str, key, value):
        if len(self._event_handlers) < 1:
            return

        event_info = {
            "key": key,
            "value": value,
        }
        event = FeatureEvent(type, info=event_info)

        super()._call_event_handlers(event)

    def __repr__(self):
        return f"{self.__class__.__name__} buffer data:\n" \
               f"{self.value.__repr__()}"


class GraphicFeatureDescriptor:
    def __init__(self, feature_name):
        self.feature_name = feature_name

    def _get_feature(self, instance):
        feature: GraphicFeature = getattr(instance, f"_{self.feature_name}")
        return feature

    def __get__(self, graphic, owner):
        f = self._get_feature(graphic)
        if isinstance(f, BufferManager):
            return f
        else:
            return f.value

    def __set__(self, graphic, value):
        feature = self._get_feature(graphic)
        if isinstance(feature, BufferManager):
            feature[:] = value
        else:
            feature.set_value(graphic, value)
