from typing import Iterable

import numpy as np


class BaseProperty:
    """A list that allows only in-place modifications and updates the ImageWidget"""

    def __init__(
        self,
        data: Iterable | None,
        image_widget,
        attribute: str,
        key_types: type | tuple[type, ...],
        value_types: type | tuple[type, ...],
    ):
        if data is not None:
            data = list(data)

        self._data = data

        self._image_widget = image_widget
        self._attribute = attribute

        self._key_types = key_types
        self._value_types = value_types

    @property
    def data(self):
        raise NotImplementedError

    def __getitem__(self, item):
        if self.data is None:
            return getattr(self._image_widget, self._attribute)[item]

        return self.data[item]

    def __setitem__(self, key, value):
        if not isinstance(key, self._key_types):
            raise TypeError

        if isinstance(key, str):
            # subplot name, find the numerical index
            for i, subplot in enumerate(self._image_widget.figure):
                if subplot.name == key:
                    key = i
                    break
            else:
                raise IndexError(f"No subplot with given name: {key}")

        if not isinstance(value, self._value_types):
            raise TypeError

        new_list = list(self.data)

        new_list[key] = value

        setattr(self._image_widget, self._attribute, new_list)

    def __repr__(self):
        return str(self.data)


class ImageWidgetData(BaseProperty):
    pass


class Indices(BaseProperty):
    def __init__(
        self,
        data: Iterable,
        image_widget,
    ):
        super().__init__(
            data,
            image_widget,
            attribute="indices",
            key_types=(int, np.integer),
            value_types=(int, np.integer),
        )

    @property
    def data(self) -> list[int]:
        return self._data

    @data.setter
    def data(self, new_data):
        self._data[:] = new_data
