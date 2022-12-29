from typing import *

from .features._base import cleanup_slice

from pygfx import WorldObject, Group
from pygfx.linalg import Vector3

from .features import GraphicFeature, PresentFeature, GraphicFeatureIndexable

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
            if isinstance(self, GraphicCollection):
                feature_instance = getattr(self[:], event_type)
            else:
                feature_instance = getattr(self, event_type)

            feature_instance.add_event_handler(self.event_handler)

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
                elif isinstance(self, GraphicCollection):
                    # if target is a GraphicCollection, then indices will be stored in collection_index
                    if event.type in self.feature_events:
                        indices = event.pick_info["collection-index"]

                    # for now we only have line collections so this works
                    else:
                        for i, item in enumerate(self._items):
                            if item.world_object is event.pick_info["world_object"]:
                                indices = i
                    target_info.target._set_feature(feature=target_info.feature, new_data=target_info.new_data, indices=indices)
                else:
                    # if target is a single graphic, then indices do not matter
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
    data: Any
    indices: Any


class GraphicCollection(BaseGraphic):
    """Graphic Collection base class"""

    pygfx_events = [
        "click"
    ]

    def __init__(self, name: str = None):
        self.name = name
        self._items: List[Graphic] = list()
        self.registered_callbacks = dict()

    @property
    def world_object(self) -> Group:
        return self._world_object

    @property
    def items(self) -> Tuple[Graphic]:
        """Get the Graphic instances within this collection"""
        return tuple(self._items)

    def add_graphic(self, graphic: Graphic, reset_index: True):
        """Add a graphic to the collection"""
        if not isinstance(graphic, self.child_type):
            raise TypeError(
                f"Can only add graphics of the same type to a collection, "
                f"You can only add {self.child_type} to a {self.__class__.__name__}, "
                f"you are trying to add a {graphic.__class__.__name__}."
            )
        self._items.append(graphic)
        if reset_index:
            self._reset_index()
        self.world_object.add(graphic.world_object)

    def remove_graphic(self, graphic: Graphic, reset_index: True):
        """Remove a graphic from the collection"""
        self._items.remove(graphic)
        if reset_index:
            self._reset_index()
        self.world_object.remove(graphic)

    def _reset_index(self):
        for new_index, graphic in enumerate(self._items):
            graphic.collection_index = new_index

    def __getitem__(self, key):
        if isinstance(key, int):
            key = [key]

        if isinstance(key, slice):
            key = cleanup_slice(key, upper_bound=len(self))
            selection_indices = range(key.start, key.stop, key.step)
            selection = self._items[key]

        # fancy-ish indexing
        elif isinstance(key, (tuple, list)):
            selection = list()
            for ix in key:
                selection.append(self._items[ix])

            selection_indices = key
        else:
            raise TypeError("Graphic Collection indexing supports int, slice, tuple or list of integers")
        return CollectionIndexer(
            parent=self,
            selection=selection,
            selection_indices=selection_indices
        )

    def __len__(self):
        return len(self._items)


class CollectionIndexer:
    """Collection Indexer"""
    def __init__(
            self,
            parent: GraphicCollection,
            selection: List[Graphic],
            selection_indices: Union[list, range],
    ):
        """

        Parameters
        ----------
        parent
        selection
        selection_indices: Union[list, range]
        """
        self._selection = selection
        self._selection_indices = selection_indices

        for attr_name in self._selection[0].__dict__.keys():
            attr = getattr(self._selection[0], attr_name)
            if isinstance(attr, GraphicFeature):
                collection_feature = CollectionFeature(
                    parent,
                    self._selection,
                    selection_indices=selection_indices,
                    feature=attr_name
                )
                collection_feature.__doc__ = f"indexable {attr_name} feature for collection"
                setattr(self, attr_name, collection_feature)

    def __setattr__(self, key, value):
        if hasattr(self, key):
            attr = getattr(self, key)
            if isinstance(attr, CollectionFeature):
                attr._set(value)
                return

        super().__setattr__(key, value)

    def __repr__(self):
        return f"{self.__class__.__name__} @ {hex(id(self))}\n" \
               f"Collection of <{len(self._selection)}> {self._selection[0].__class__.__name__}"


class CollectionFeature:
    """Collection Feature"""
    def __init__(
            self,
            parent: GraphicCollection,
            selection: List[Graphic],
            selection_indices, feature: str
    ):
        self._selection = selection
        self._selection_indices = selection_indices
        self._feature = feature

        self._feature_instances: List[GraphicFeature] = list()

        for graphic in self._selection:
            fi = getattr(graphic, self._feature)
            self._feature_instances.append(fi)

        if isinstance(fi, GraphicFeatureIndexable):
            self._indexable = True
        else:
            self._indexable = False

    def _set(self, value):
        self[:] = value

    def __getitem__(self, item):
        # only for indexable graphic features
        return [fi[item] for fi in self._feature_instances]

    def __setitem__(self, key, value):
        if self._indexable:
            for fi in self._feature_instances:
                fi[key] = value

        else:
            for fi in self._feature_instances:
                fi._set(value)

    def add_event_handler(self, handler: callable):
        for fi in self._feature_instances:
            fi.add_event_handler(handler)

    def remove_event_handler(self, handler: callable):
        for fi in self._feature_instances:
            fi.remove_event_handler(handler)

    def block_events(self, b: bool):
        for fi in self._feature_instances:
            fi.block_events(b)

    def __repr__(self):
        return f"Collection feature for: <{self._feature}>"
