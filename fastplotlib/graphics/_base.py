from typing import *

from pygfx import WorldObject
from pygfx.linalg import Vector3

from .features import GraphicFeature, PresentFeature
#from ._collection import GraphicCollection

from abc import ABC, abstractmethod
from dataclasses import dataclass

class BaseGraphic:
    def __init_subclass__(cls, **kwargs):
        """set the type of the graphic in lower case like "image", "line_collection", etc."""
        cls.type = cls.__name__.lower().replace("graphic", "").replace("collection", "_collection")
        super().__init_subclass__(**kwargs)


class Graphic(BaseGraphic):
    pygfx_events = [
        "click"
    ]

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

    def link(self, event_type: str, target: Any, feature: str, new_data: Any, callback_function: callable = None):
        if event_type in self.pygfx_events:
            self.world_object.add_event_handler(self.event_handler, event_type)
        elif event_type in self.feature_events:
            feature = getattr(self, event_type)
            feature.add_event_handler(self.event_handler, event_type)
        else:
            raise ValueError("event not possible")

        if event_type in self.registered_callbacks.keys():
            self.registered_callbacks[event_type].append(
                CallbackData(target=target, feature=feature, new_data=new_data, callback_function=callback_function))
        else:
            self.registered_callbacks[event_type] = list()
            self.registered_callbacks[event_type].append(
                CallbackData(target=target, feature=feature, new_data=new_data, callback_function=callback_function))

    def event_handler(self, event):
        if event.type in self.registered_callbacks.keys():
            for target_info in self.registered_callbacks[event.type]:
                if target_info.callback_function is not None:
                    # if callback_function is not None, then callback function should handle the entire event
                    target_info.callback_function(source=self, target=target_info.target, event=event, new_data=target_info.new_data)
                # elif isinstance(self, GraphicCollection):
                #     indices = event.pick_info["collection_index"]
                #     target_info.target._set_feature(feature=target_info.feature, new_data=target_info.new_data, indices=indices)
                else:
                    target_info.target._set_feature(feature=target_info.feature, new_data=target_info.new_data,
                                                    indices=None)

@dataclass
class CallbackData:
    """Class for keeping track of the info necessary for interactivity after event occurs."""
    target: Any
    feature: str
    new_data: Any
    callback_function: callable = None


@dataclass
class PreviouslyModifiedData:
    """Class for keeping track of previously modified data at indices"""
    previous_data: Any
    previous_indices: Any