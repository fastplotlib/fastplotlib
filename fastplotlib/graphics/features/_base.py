from abc import ABC, abstractmethod
from inspect import getfullargspec
from warnings import warn
from typing import *
import weakref

import numpy as np
from pygfx import Buffer, Texture


supported_dtypes = [
    np.uint8,
    np.uint16,
    np.uint32,
    np.int8,
    np.int16,
    np.int32,
    np.float16,
    np.float32
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
                raise TypeError("Unsupported type, supported array types must be int or float dtypes")

    return array


class FeatureEvent:
    """
    type: <feature_name>, example: "colors"
    pick_info: dict in the form:
        {
            "index": indices where feature data was changed, ``range`` object or List[int],
            "world_object": world object the feature belongs to,
            "new_values": the new values
        }
    """
    def __init__(self, type: str, pick_info: dict):
        self.type = type
        self.pick_info = pick_info

    def __repr__(self):
        return f"{self.__class__.__name__} @ {hex(id(self))}\n" \
               f"type: {self.type}\n" \
               f"pick_info: {self.pick_info}\n"


class GraphicFeature(ABC):
    def __init__(self, parent, data: Any, collection_index: int = None):
        """

        Parameters
        ----------
        parent

        data: Any

        collection_index: int
            if part of a collection, index of this graphic within the collection

        """
        self._parent = weakref.proxy(parent)

        self._data = to_gpu_supported_dtype(data)

        self._collection_index = collection_index
        self._event_handlers = list()
        self._block_events = False

    def __call__(self, *args, **kwargs):
        return self._data

    def block_events(self, b: bool):
        self._block_events = b

    @abstractmethod
    def _set(self, value):
        pass

    def _parse_set_value(self, value):
        if isinstance(value, GraphicFeature):
            return value()

        return value

    def add_event_handler(self, handler: callable):
        """
        Add an event handler. All added event handlers are called when this feature changes.
        The `handler` can optionally accept ``FeatureEvent`` as the first and only argument.
        The ``FeatureEvent`` only has two attributes, `type` which denotes the type of event
        as a str in the form of "<feature_name>-changed", such as "color-changed".

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
        if handler not in self._event_handlers:
            raise KeyError(f"event handler {handler} not registered.")

        self._event_handlers.pop(handler)

    #TODO: maybe this can be implemented right here in the base class
    @abstractmethod
    def _feature_changed(self, key: Union[int, slice, Tuple[slice]], new_data: Any):
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
            except:
                warn(f"Event handler {func} has an unresolvable argspec, calling it without arguments")
                func()


def cleanup_slice(key: Union[int, slice], upper_bound) -> Union[slice, int]:
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
        raise IndexError("Index out of bounds")

    step = key.step
    if step is None:
        step = 1

    return slice(start, stop, step)


class GraphicFeatureIndexable(GraphicFeature):
    """And indexable Graphic Feature, colors, data, sizes etc."""

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
    def buffer(self) -> Union[Buffer, Texture]:
        pass

    @property
    def _upper_bound(self) -> int:
        return self._data.shape[0]

    def _update_range_indices(self, key):
        """Currently used by colors and positions data"""
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
        else:
            raise TypeError("must pass int or slice to update range")

