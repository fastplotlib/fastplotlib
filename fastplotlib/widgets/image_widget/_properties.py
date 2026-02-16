from pprint import pformat
from typing import Iterable

import numpy as np

from ._processor import NDImageProcessor


class ImageWidgetProperty:
    __class_getitem__ = classmethod(type(list[int]))

    def __init__(
        self,
        image_widget,
        attribute: str,
    ):
        self._image_widget = image_widget
        self._image_processors: list[NDImageProcessor] = image_widget._image_processors
        self._attribute = attribute

    def _get_key(self, key: slice | int | np.integer | str) -> int | slice:
        if not isinstance(key, (slice | int, np.integer, str)):
            raise TypeError(
                f"can index `{self._attribute}` only with a <slice>, <int>, or a <str> indicating the subplot name."
                f"You tried to index with: {key}"
            )

        if isinstance(key, str):
            for i, subplot in enumerate(self._image_widget.figure):
                if subplot.name == key:
                    key = i
                    break
            else:
                raise IndexError(f"No subplot with given name: {key}")

        return key

    def __getitem__(self, key):
        key = self._get_key(key)
        # return image processor attribute at this index
        if isinstance(key, (int, np.integer)):
            return getattr(self._image_processors[key], self._attribute)

        # if it's a slice
        processors = self._image_processors[key]

        return tuple(getattr(p, self._attribute) for p in processors)

    def __setitem__(self, key, value):
        key = self._get_key(key)

        # get the values from the ImageWidget property
        new_values = list(getattr(p, self._attribute) for p in self._image_processors)

        # set the new value at this slice
        new_values[key] = value

        # call the setter
        setattr(self._image_widget, self._attribute, new_values)

    def __iter__(self):
        for image_processor in self._image_processors:
            yield getattr(image_processor, self._attribute)

    def __repr__(self):
        return f"{self._attribute}: {pformat(self[:])}"

    def __eq__(self, other):
        return self[:] == other


class Indices:
    def __init__(
        self,
        indices: list[int],
        image_widget,
    ):
        self._data = indices

        self._image_widget = image_widget

    def __iter__(self):
        for i in self._data:
            yield i

    def _parse_key(self, key: int | np.integer | str) -> int:
        if not isinstance(key, (int, np.integer, str)):
            raise TypeError(
                f"indices can only be indexed with <int> or <str> types, you have used: {key}"
            )

        if isinstance(key, str):
            # get integer index from user's names
            names = self._image_widget._slider_dim_names
            if key not in names:
                raise KeyError(
                    f"dim with name: {key} not found in slider_dim_names, current names are: {names}"
                )

            key = names.index(key)

        return key

    def __getitem__(self, key: int | np.integer | str) -> int | tuple[int]:
        if isinstance(key, str):
            key = self._parse_key(key)

        return self._data[key]

    def __setitem__(self, key, value):
        key = self._parse_key(key)

        if not isinstance(value, (int, np.integer)):
            raise TypeError(
                f"indices values can only be set with integers, you have tried to set the value: {value}"
            )

        new_indices = list(self._data)
        new_indices[key] = value

        self._image_widget.indices = new_indices

    def _fpl_set(self, values):
        self._data[:] = values

    def pop_dim(self):
        self._data.pop(0)

    def push_dim(self):
        self._data.insert(0, 0)

    def __len__(self):
        return len(self._data)

    def __eq__(self, other):
        return self._data == other

    def __repr__(self):
        return f"indices: {self._data}"
