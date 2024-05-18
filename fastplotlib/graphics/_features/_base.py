from abc import abstractmethod
from inspect import getfullargspec
from warnings import warn
from typing import Any, Literal

import numpy as np
from numpy.typing import NDArray

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


class FeatureEvent:
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

    def __init__(self, type: str, pick_info: dict):
        self.type = type
        self.pick_info = pick_info

    def __repr__(self):
        return (
            f"{self.__class__.__name__} @ {hex(id(self))}\n"
            f"type: {self.type}\n"
            f"pick_info: {self.pick_info}\n"
        )


class GraphicFeature:
    def __init__(self, **kwargs):
        self._event_handlers = list()
        self._block_events = False
        self.collection_index: int = None

    @property
    def value(self) -> Any:
        raise NotImplemented

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
        Add an event handler. All added event handlers are calledcollection_ind when this feature changes.

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

    # TODO: maybe this can be implemented right here in the base class
    @abstractmethod
    def _feature_changed(self,new_data: Any, key: int | slice | tuple[slice] | None = None):
        """Called whenever a feature changes, and it calls all funcs in self._event_handlers"""
        pass

    def _call_event_handlers(self, event_data: FeatureEvent):
        if self._block_events:
            return

        for func in self._event_handlers:
            try:
                args = getfullargspec(func).args

                if len(args) > 0:
                    if args[0] == "self" and not len(args) > 1:
                        func()
                    else:
                        func(event_data)
                else:
                    func()
            except TypeError:
                warn(
                    f"Event handler {func} has an unresolvable argspec, calling it without arguments"
                )
                func()

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

    @property
    def value(self) -> NDArray:
        return self.buffer.data

    @property
    def buffer(self) -> pygfx.Buffer | pygfx.Texture:
        return self._buffer

    def cleanup_key(self, key: int | np.ndarray[int, bool] | slice | tuple[slice, ...]) -> int | np.ndarray | range | tuple[range, ...]:
        """
        Cleanup slice indices for setitem, returns positive indices. Converts negative indices to positive if necessary.

        Returns a cleaned up key corresponding to only the first dimension.
        """
        upper_bound = self.value.shape[0]

        if isinstance(key, int):
            if abs(key) > upper_bound:  # absolute value in case negative index
                raise IndexError(f"key value: {key} out of range for dimension with size: {upper_bound}")
            return key

        elif isinstance(key, np.ndarray):
            if key.ndim > 1:
                raise TypeError(f"Can only use 1D boolean or integer arrays for fancy indexing")

            # if boolean array convert to integer array of indices
            if key.dtype == bool:
                key = np.nonzero(key)[0]

            if key.size < 1:
                return None

            # make sure indices within bounds of feature buffer range
            if key[-1] > upper_bound:
                raise IndexError(
                    f"Index: `{key[-1]}` out of bounds for feature array of size: `{upper_bound}`"
                )

            # make sure indices are integers
            if np.issubdtype(key.dtype, np.integer):
                return key

            raise TypeError(f"Can only use 1D boolean or integer arrays for fancy indexing graphic features")

        elif isinstance(key, tuple):
            # multiple dimension slicing
            if not all([isinstance(k, (int, slice, range, np.ndarray)) for k in key]):
                raise TypeError(key)

            cleaned_tuple = list()
            # cleanup the key for each dim
            for k in key:
                cleaned_tuple.append(self.cleanup_key(k))

            return key

        if not isinstance(key, (slice, range)):
            raise TypeError("Must pass slice or int object")

        start = key.start if key.start is not None else 0
        stop = key.stop if key.stop is not None else self.value.shape[0] - 1
        # absolute value of the step in case it's negative
        # since we convert start and stop to be positive below it is fine for step to be converted to positive
        step = abs(key.step) if key.step is not None else 1

        # modulus in case of negative indices
        start %= upper_bound
        stop %= upper_bound

        if start > stop:
            raise ValueError(f"start index: {start} greater than stop index: {stop}")

        return range(start, stop, step)

    def __getitem__(self, item):
        return self.buffer.data[item]

    def __setitem__(self, key, value):
        raise NotImplementedError

    def _update_range(self, key):
        # assumes key is already cleaned up
        if isinstance(key, range):
            offset = key.start
            size = key.stop - key.start

        elif isinstance(key, np.ndarray):
            offset = key.min()
            size = key.max() - offset

        elif isinstance(key, int):
            offset = key
            size = 1
        elif isinstance(key, tuple):
            key: range | slice = key[0]
            upper_bound = self.value.shape[0]

            offset = key.start if key.start is not None else 0
            # size is number of points so do not subtract 1 from upper bound like in cleanup_key for indexing
            stop = key.stop if key.stop is not None else upper_bound

            offset %= upper_bound
            stop %= upper_bound + 1

            size = stop - offset

        else:
            raise TypeError(key)

        self.buffer.update_range(offset=offset, size=size)

    def __repr__(self):
        return f"{self.__class__.__name__} buffer data:\n" \
               f"{self.value.__repr__()}"


class GraphicFeatureDescriptor:
    def __init__(self, name):
        self.name = name

    def _get_feature(self, instance):
        feature: GraphicFeature = getattr(instance, f"_{self.name}")
        return feature

    def __get__(self, instance, owner):
        return self._get_feature(instance)

    def __set__(self, obj, value):
        feature = self._get_feature(obj)
        feature[:] = value
