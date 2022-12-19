from typing import *

import numpy as np
import pygfx

from fastplotlib.utils import get_colors, map_labels_to_colors

from abc import ABC, abstractmethod
from dataclasses import dataclass
# from .linecollection import LineCollection

class Graphic:
    def __init__(
            self,
            data,
            colors: np.ndarray = None,
            colors_length: int = None,
            cmap: str = None,
            alpha: float = 1.0,
            name: str = None
    ):
        self.data = data.astype(np.float32)
        self.colors = None

        self.name = name
        self.registered_callbacks = dict()

        # if colors_length is None:
        #     colors_length = self.data.shape[0]

        if colors is not False:
            self._set_colors(colors, colors_length, cmap, alpha, )

    def _set_colors(self, colors, colors_length, cmap, alpha):
        if colors_length is None:
            colors_length = self.data.shape[0]

        if colors is None and cmap is None:  # just white
            self.colors = np.vstack([[1., 1., 1., 1.]] * colors_length).astype(np.float32)

        elif (colors is None) and (cmap is not None):
            self.colors = get_colors(n_colors=colors_length, cmap=cmap, alpha=alpha)

        elif (colors is not None) and (cmap is None):
            # assume it's already an RGBA array
            colors = np.array(colors)
            if colors.shape == (1, 4) or colors.shape == (4,):
                self.colors = np.vstack([colors] * colors_length).astype(np.float32)
            elif colors.ndim == 2 and colors.shape[1] == 4 and colors.shape[0] == colors_length:
                self.colors = colors.astype(np.float32)
            else:
                raise ValueError(f"Colors array must have ndim == 2 and shape of [<n_datapoints>, 4]")

        elif (colors is not None) and (cmap is not None):
            if colors.ndim == 1 and np.issubdtype(colors.dtype, np.integer):
                # assume it's a mapping of colors
                self.colors = np.array(map_labels_to_colors(colors, cmap, alpha=alpha)).astype(np.float32)

        else:
            raise ValueError("Unknown color format")

    @property
    def children(self) -> pygfx.WorldObject:
        return self.world_object.children

    def update_data(self, data: Any):
        pass

    def __repr__(self):
        if self.name is not None:
            return f"'{self.name}' fastplotlib.{self.__class__.__name__} @ {hex(id(self))}"
        else:
            return f"fastplotlib.{self.__class__.__name__} @ {hex(id(self))}"

class Interaction(ABC):
    @property
    @abstractmethod
    def indices(self) -> Any:
        pass

    @indices.setter
    @abstractmethod
    def indices(self, indices: Any):
        pass

    @property
    @abstractmethod
    def features(self) -> List[str]:
        pass

    @abstractmethod
    def _set_feature(self, feature: str, new_data: Any, indices: Any):
        pass

    @abstractmethod
    def _reset_feature(self, feature: str, old_data: Any, indices: Any):
        pass

    def link(self, event_type: str, target: Graphic, feature: str, new_data: Any, indices_mapper: callable = None):
        valid_events = ["click"]
        if event_type in valid_events:
            self.world_object.add_event_handler(self.event_handler, event_type)
        else:
            raise ValueError("event not possible")

        if event_type in self.registered_callbacks.keys():
            self.registered_callbacks[event_type].append(
                CallbackData(target=target, feature=feature, new_data=new_data, old_data=getattr(target, feature).copy()))
        else:
            self.registered_callbacks[event_type] = list()
            self.registered_callbacks[event_type].append(
                CallbackData(target=target, feature=feature, new_data=new_data, old_data=getattr(target, feature).copy()))

    def event_handler(self, event):
        if event.type in self.registered_callbacks.keys():
            for target_info in self.registered_callbacks[event.type]:
                target_info.target._reset_feature(feature=target_info.feature, old_data=target_info.old_data, indices=None)
                target_info.target._set_feature(feature=target_info.feature, new_data=target_info.new_data, indices=None)

@dataclass
class CallbackData:
    """Class for keeping track of the info necessary for interactivity after event occurs."""
    target: Graphic
    feature: str
    new_data: Any
    old_data: Any
