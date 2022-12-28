from typing import *

from pygfx import WorldObject
from pygfx.linalg import Vector3

from .features import GraphicFeature, PresentFeature

from abc import ABC, abstractmethod
from dataclasses import dataclass

class BaseGraphic:
    def __init_subclass__(cls, **kwargs):
        """set the type of the graphic in lower case like "image", "line_collection", etc."""
        cls.type = cls.__name__.lower().replace("graphic", "").replace("collection", "_collection")
        super().__init_subclass__(**kwargs)


class Graphic(BaseGraphic):
    def __init__(
            self,
            name: str = None
    ):
        """

        Parameters
        ----------
        name: str, optional
            name this graphic, makes it indexable within plots

        """

        self.name = name
        self.registered_callbacks = dict()
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
    def world_object(self) -> WorldObject:
        return self._world_object

    @property
    def position(self) -> Vector3:
        """The position of the graphic"""
        return self.world_object.position

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
    def children(self) -> WorldObject:
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