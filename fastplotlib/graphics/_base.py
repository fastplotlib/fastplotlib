from typing import *

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

        valid_features = ["visible"]
        for attr_name in self.__dict__.keys():
            attr = getattr(self, attr_name)
            if isinstance(attr, GraphicFeature):
                valid_features.append(attr_name)

        self._valid_features = tuple(valid_features)

    @property
    def world_object(self) -> pygfx.WorldObject:
        return self._world_object

    @property
    def interact_features(self) -> Tuple[str]:
        """The features for this ``Graphic`` that support interaction."""
        return self._valid_features

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
