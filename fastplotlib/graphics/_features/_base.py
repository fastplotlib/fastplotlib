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

    @property
    def data(self) -> Any:
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
            bdata = np.zeros(data.shape)
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
    def data(self) -> NDArray:
        return self.buffer.data

    @property
    def buffer(self) -> pygfx.Buffer | pygfx.Texture:
        return self._buffer

    def __getitem__(self, item):
        return self.buffer.data[item]

    def __setitem__(self, key, value):
        raise NotImplementedError

    def _update_range(self, offset, size):
        self.buffer.update_range(offset=offset, size=size)

    def __repr__(self):
        return f"{self.__class__.__name__} buffer data:\n" \
               f"{self.data.__repr__()}"


def parse_colors(value, n):
    """parse colors using pygfx and return RGBA array for each vertex"""
    if isinstance(value, str):
        return np.array([pygfx.Color(value)] * n)

    return value


def parse_colors(key, value, n_colors, max_n_colors):
    """

    Parameters
    ----------
    key: slice

    value

    n_colors

    max_n_colors: basically data.shape[0]

    Returns
    -------

    """
    pass


class ColorFeature(BufferManager):
    """Manage color buffer for positions type objects"""

    def __init__(self, data: str | np.ndarray, n_colors: int, isolated_buffer: bool):
        if not isinstance(data, np.ndarray):
            # isolated buffer is only useful when data is a numpy array
            isolated_buffer = False

        colors = parse_colors(data, n_colors)

        super().__init__(colors, isolated_buffer)

    def __setitem__(self, key, value):
        if isinstance(value, BufferManager):
            # trying to set feature from another feature instance
            value = value.data

        key = self.cleanup_slice(key)

        colors = parse_colors(value, len(key))

        self.buffer.data[key] = colors

        self._update_range(key.start, key.stop - key.start)


def cleanup_slice(key: int | slice, upper_bound) -> slice | int:
    """

    If the key in an `int`, it just returns it. Otherwise,
    it parses it and removes the `None` vals and replaces
    them with corresponding values that can be used to
    create a `range`, get `len` etc.

    Parameters
    ----------
    key
    upper_bound

    Returns
    -------

    """
    if isinstance(key, int):
        return key

    if isinstance(key, np.ndarray):
        return cleanup_array_slice(key, upper_bound)

    if isinstance(key, tuple):
        # if tuple of slice we only need the first obj
        # since the first obj is the datapoint indices
        if isinstance(key[0], slice):
            key = key[0]
        else:
            raise TypeError("Tuple slicing must have slice object in first position")

    if not isinstance(key, slice):
        raise TypeError("Must pass slice or int object")

    start = key.start
    stop = key.stop
    step = key.step
    for attr in [start, stop, step]:
        if attr is None:
            continue
        if attr < 0:
            raise IndexError("Negative indexing not supported.")

    if start is None:
        start = 0

    if stop is None:
        stop = upper_bound

    elif stop > upper_bound:
        raise IndexError(
            f"Index: `{stop}` out of bounds for feature array of size: `{upper_bound}`"
        )

    step = key.step
    if step is None:
        step = 1

    return slice(start, stop, step)


def cleanup_array_slice(key: np.ndarray, upper_bound) -> np.darray | None:
    """
    Cleanup numpy array used for fancy indexing, make sure key[-1] <= upper_bound.

    Returns None if nothing to change.

    Parameters
    ----------
    key: np.ndarray
        integer or boolean array

    upper_bound

    Returns
    -------
    np.ndarray
        integer indexing array

    """

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

    raise TypeError(f"Can only use 1D boolean or integer arrays for fancy indexing")


class GraphicFeatureIndexable(GraphicFeature):
    """An indexable Graphic Feature, colors, data, sizes etc."""

    def _set(self, value):
        value = self._parse_set_value(value)
        self[:] = value

    @abstractmethod
    def __getitem__(self, item):
        pass

    @abstractmethod
    def __setitem__(self, key, value):
        pass

    @abstractmethod
    def _update_range(self, key):
        pass

    @property
    @abstractmethod
    def buffer(self) -> pygfx.Buffer | pygfx.Texture:
        """Underlying buffer for this feature"""
        pass

    @property
    def _upper_bound(self) -> int:
        return self._data.shape[0]

    def _update_range_indices(self, key):
        """Currently used by colors and positions data"""
        if not isinstance(key, np.ndarray):
            key = cleanup_slice(key, self._upper_bound)

        if isinstance(key, int):
            self.buffer.update_range(key, size=1)
            return

        # else if it's a slice obj
        if isinstance(key, slice):
            if key.step == 1:  # we cleaned up the slice obj so step of None becomes 1
                # update range according to size using the offset
                self.buffer.update_range(offset=key.start, size=key.stop - key.start)

            else:
                step = key.step
                # convert slice to indices
                ixs = range(key.start, key.stop, step)
                for ix in ixs:
                    self.buffer.update_range(ix, size=1)

        # TODO: See how efficient this is with large indexing
        elif isinstance(key, np.ndarray):
            self.buffer.update_range()

        else:
            raise TypeError("must pass int or slice to update range")
