from typing import *
import numpy as np

import pygfx

from ..utils import get_colors
from .features import GraphicFeature, DataFeature, ColorFeature, PresentFeature

from abc import ABC, abstractmethod
from dataclasses import dataclass

class Graphic:
    def __init__(
            self,
            data,
            colors: Any = False,
            n_colors: int = None,
            cmap: str = None,
            alpha: float = 1.0,
            name: str = None
    ):
        """

        Parameters
        ----------
        data: array-like
            data to show in the graphic, must be float32.
            Automatically converted to float32 for numpy arrays.
            Tensorflow Tensors also work but this is not fully
            tested and might not be supported in the future.

        colors: Any
            if ``False``, no color generation is performed, cmap is also ignored.

        n_colors

        cmap: str
            name of colormap to use

        alpha: float, optional
            alpha value for the colors

        name: str, optional
            name this graphic, makes it indexable within plots

        """
        # self.data = data.astype(np.float32)
        self.data = DataFeature(parent=self, data=data, graphic_name=self.__class__.__name__)
        self.colors = None

        self.name = name
        self.registered_callbacks = dict()

        if n_colors is None:
            n_colors = self.data.feature_data.shape[0]

        if cmap is not None and colors is not False:
            colors = get_colors(n_colors=n_colors, cmap=cmap, alpha=alpha)

        if colors is not False:
            self.colors = ColorFeature(parent=self, colors=colors, n_colors=n_colors, alpha=alpha)

        # different from visible, toggles the Graphic presence in the Scene
        # useful for bbox calculations to ignore these Graphics
        self.present = PresentFeature(parent=self)

        #valid_features = ["visible"]
        self._feature_events = list()
        for attr_name in self.__dict__.keys():
            attr = getattr(self, attr_name)
            if isinstance(attr, GraphicFeature):
                self._feature_events.append(attr_name)

        self._feature_events = tuple(self._feature_events)
        self._pygfx_events = ("click",)

    @property
    def world_object(self) -> pygfx.WorldObject:
        return self._world_object

    @property
    def visible(self) -> bool:
        return self.world_object.visible

    @visible.setter
    def visible(self, v):
        """Toggle the visibility of this Graphic"""
        self.world_object.visible = v

    @property
    def children(self) -> pygfx.WorldObject:
        return self.world_object.children

    def __setattr__(self, key, value):
        if hasattr(self, key):
            attr = getattr(self, key)
            if isinstance(attr, GraphicFeature):
                attr._set(value)
                return

        super().__setattr__(key, value)

    def __repr__(self):
        if self.name is not None:
            return f"'{self.name}' fastplotlib.{self.__class__.__name__} @ {hex(id(self))}"
        else:
            return f"fastplotlib.{self.__class__.__name__} @ {hex(id(self))}"

class Interaction(ABC):
    @abstractmethod
    def _set_feature(self, feature: str, new_data: Any, indices: Any):
        pass

    @abstractmethod
    def _reset_feature(self, feature: str):
        pass

    def link(self, event_type: str, target: Any, feature: str, new_data: Any, indices_mapper: callable = None):
        if event_type in self._pygfx_events:
            self.world_object.add_event_handler(self.event_handler, event_type)
        elif event_type in self._feature_events:
            feature = getattr(self, event_type)
            feature.add_event_handler(self.event_handler, event_type)
        else:
            raise ValueError("event not possible")

        if event_type in self.registered_callbacks.keys():
            self.registered_callbacks[event_type].append(
                CallbackData(target=target, feature=feature, new_data=new_data, indices_mapper=indices_mapper))
        else:
            self.registered_callbacks[event_type] = list()
            self.registered_callbacks[event_type].append(
                CallbackData(target=target, feature=feature, new_data=new_data, indices_mapper=indices_mapper))

    def event_handler(self, event):
        event_info = event.pick_info
        #click_info = np.array(event.pick_info["index"])
        if event.type in self.registered_callbacks.keys():
            for target_info in self.registered_callbacks[event.type]:
                if target_info.indices_mapper is not None:
                    indices = target_info.indices_mapper(source=self, target=target_info.target, indices=click_info)
                else:
                    indices = None
                # set feature of target at indice using new data
                target_info.target._set_feature(feature=target_info.feature, new_data=target_info.new_data, indices=indices)

@dataclass
class CallbackData:
    """Class for keeping track of the info necessary for interactivity after event occurs."""
    target: Any
    feature: str
    new_data: Any
    indices_mapper: callable = None

@dataclass
class PreviouslyModifiedData:
    """Class for keeping track of previously modified data at indices"""
    previous_data: Any
    previous_indices: Any
