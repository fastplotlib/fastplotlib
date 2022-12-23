from abc import ABC, abstractmethod
from inspect import getfullargspec
from warnings import warn
from typing import *

import numpy as np
from pygfx import Buffer


class FeatureEvent:
    """
    type: <feature_name>-<changed>, example: "color-changed"
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
    def __init__(self, parent, data: Any):
        self._parent = parent
        if isinstance(data, np.ndarray):
            data = data.astype(np.float32)

        self._data = data
        self._event_handlers = list()

    @property
    def feature_data(self):
        """graphic feature data managed by fastplotlib, do not modify directly"""
        return self._data

    @abstractmethod
    def _set(self, value):
        pass

    @abstractmethod
    def __repr__(self):
        pass

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

    #TODO: maybe this can be implemented right here in the base class
    @abstractmethod
    def _feature_changed(self, key: Union[int, slice, Tuple[slice]], new_data: Any):
        """Called whenever a feature changes, and it calls all funcs in self._event_handlers"""
        pass

    def _call_event_handlers(self, event_data: FeatureEvent):
        for func in self._event_handlers:
            try:
                if len(getfullargspec(func).args) > 0:
                    func(event_data)
            except:
                warn(f"Event handler {func} has an unresolvable argspec, trying it anyways.")
                func(event_data)
            else:
                func()


def cleanup_slice(key: Union[int, slice], upper_bound) -> Union[slice, int]:
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
    def _buffer(self) -> Buffer:
        pass

    @property
    def _upper_bound(self) -> int:
        return self.feature_data.shape[0]

    def _update_range_indices(self, key):
        """Currently used by colors and data"""
        key = cleanup_slice(key, self._upper_bound)

        if isinstance(key, int):
            self._buffer.update_range(key, size=1)
            return

        # else if it's a slice obj
        if isinstance(key, slice):
            if key.step == 1:  # we cleaned up the slice obj so step of None becomes 1
                # update range according to size using the offset
                self._buffer.update_range(offset=key.start, size=key.stop - key.start)

            else:
                step = key.step
                # convert slice to indices
                ixs = range(key.start, key.stop, step)
                for ix in ixs:
                    self._buffer.update_range(ix, size=1)
        else:
            raise TypeError("must pass int or slice to update range")


