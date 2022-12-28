from typing import *

import numpy as np

from pygfx import Group

from ._base import BaseGraphic, Graphic
from .features._base import GraphicFeature, GraphicFeatureIndexable, cleanup_slice


class GraphicCollection(BaseGraphic):
    """Graphic Collection base class"""
    def __init__(self, name: str = None):
        self.name = name
        self._items: List[Graphic] = list()

    @property
    def world_object(self) -> Group:
        return self._world_object

    @property
    def items(self) -> Tuple[Graphic]:
        """Get the Graphic instances within this collection"""
        return tuple(self._items)

    def add_graphic(self, graphic: Graphic):
        """Add a graphic to the collection"""
        if not isinstance(graphic, self.child_type):
            raise TypeError(
                f"Can only add graphics of the same type to a collection, "
                f"You can only add {self.child_type} to a {self.__class__.__name__}, "
                f"you are trying to add a {graphic.__class__.__name__}."
            )
        self._items.append(graphic)
        self.reset_index()
        self.world_object.add(graphic.world_object)

    def remove_graphic(self, graphic: Graphic):
        """Remove a graphic from the collection"""
        self._items.remove(graphic)
        self.reset_index()
        self.world_object.remove(graphic)

    def reset_index(self):
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
            key = None

    def add_event_handler(self, handler: callable):
        for fi in self._feature_instances:
            fi.add_event_handler(handler)

    def remove_event_handler(self, handler: callable):
        for fi in self._feature_instances:
            fi.remove_event_handler(handler)

    def __repr__(self):
        return f"Collection feature for: <{self._feature}>"
