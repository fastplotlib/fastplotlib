from typing import *

import numpy as np
import pygfx

from fastplotlib.utils import get_colors, map_labels_to_colors

from abc import ABC, abstractmethod
from dataclasses import dataclass

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
    def indices(self) -> Any:
        return self.indices

    @indices.setter
    def indices(self, indices: Any):
        self.indices = indices

    @property
    @abstractmethod
    def features(self) -> List[str]:
        pass

    @abstractmethod
    def _set_feature(self, feature: str, new_data: Any, indices: Any):
        pass

    @abstractmethod
    def _reset_feature(self, feature: str, old_data: Any):
        pass

    def link(self, event_type: str, target: Any, feature: str, new_data: Any, indices_mapper: callable = None):
        valid_events = ["click"]
        if event_type in valid_events:
            self.world_object.add_event_handler(self.event_handler, event_type)
        else:
            raise ValueError("event not possible")

        if isinstance(target.data, List):
            old_data = list()
            for line in target.data:
                old_data.append(getattr(line, feature).copy())
        else:
            old_data = getattr(target, feature).copy()

        if event_type in self.registered_callbacks.keys():
            self.registered_callbacks[event_type].append(
                CallbackData(target=target, feature=feature, new_data=new_data, old_data=old_data, indices_mapper=indices_mapper))
        else:
            self.registered_callbacks[event_type] = list()
            self.registered_callbacks[event_type].append(
                CallbackData(target=target, feature=feature, new_data=new_data, old_data=old_data, indices_mapper=indices_mapper))

    def event_handler(self, event):
        if event.type == "click":
            # storing click information for each click in self.indices
            #self.indices(np.array(event.pick_info["index"]))
            click_info = np.array(event.pick_info["index"])
        if event.type in self.registered_callbacks.keys():
            for target_info in self.registered_callbacks[event.type]:
                # need to map the indices to the target using indices_mapper
                if target_info.indices_mapper is not None:
                    indices = target_info.indices_mapper(target=target_info.target, indices=click_info)
                else:
                    indices = None
                # reset feature of target using stored old data
                target_info.target._reset_feature(feature=target_info.feature, old_data=target_info.old_data)
                # set feature of target at indice using new data
                target_info.target._set_feature(feature=target_info.feature, new_data=target_info.new_data[indices], indices=indices)

@dataclass
class CallbackData:
    """Class for keeping track of the info necessary for interactivity after event occurs."""
    target: Any
    feature: str
    new_data: Any
    old_data: Any
    indices_mapper: callable = None
