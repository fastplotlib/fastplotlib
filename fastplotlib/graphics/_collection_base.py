from contextlib import suppress
from typing import Any

import numpy as np

from ._base import Graphic


class CollectionProperties:
    """
    Properties common to all Graphic Collections

    Allows getting and setting the common properties of the individual graphics in the collection
    """

    def _set_feature(self, feature, values):
        if not len(values) == len(self):
            raise IndexError

        for g, v in zip(self, values):
            setattr(g, feature, v)

    @property
    def names(self) -> np.ndarray[str | None]:
        """get or set the name of the individual graphics in the collection"""
        return np.asarray([g.name for g in self])

    @names.setter
    def names(self, values: np.ndarray[str] | list[str]):
        self._set_feature("name", values)

    @property
    def metadatas(self) -> np.ndarray[str | None]:
        """get or set the metadata of the individual graphics in the collection"""
        return np.asarray([g.metadata for g in self])

    @metadatas.setter
    def metadatas(self, values: np.ndarray[str] | list[str]):
        self._set_feature("metadata", values)

    @property
    def offsets(self) -> np.ndarray:
        """get or set the offset of the individual graphics in the collection"""
        return np.stack([g.offset for g in self])

    @offsets.setter
    def offsets(self, values: np.ndarray | list[np.ndarray]):
        self._set_feature("offset", values)

    @property
    def rotations(self) -> np.ndarray:
        """get or set the rotation of the individual graphics in the collection"""
        return np.stack([g.rotation for g in self])

    @rotations.setter
    def rotations(self, values: np.ndarray | list[np.ndarray]):
        self._set_feature("rotation", values)

    # TODO: how to work with deleted feature in a collection

    @property
    def visibles(self) -> np.ndarray[bool]:
        """get or set the offsets of the individual graphics in the collection"""
        return np.asarray([g.visible for g in self])

    @visibles.setter
    def visibles(self, values: np.ndarray[bool] | list[bool]):
        self._set_feature("visible", values)


class CollectionIndexer(CollectionProperties):
    """Collection Indexer"""

    def __init__(self, selection: np.ndarray[Graphic], features: set[str]):
        """

        Parameters
        ----------

        selection: np.ndarray of Graphics
            array of the selected Graphics from the parent GraphicCollection based on the ``selection_indices``

        """

        if isinstance(selection, Graphic):
            selection = np.asarray([selection])

        self._selection = selection
        self.features = features

    @property
    def graphics(self) -> np.ndarray[Graphic]:
        """Returns an array of the selected graphics"""
        return tuple(self._selection)

    def add_event_handler(self, *args):
        """
        Register an event handler.

        Parameters
        ----------
        callback: callable, the first argument
            Event handler, must accept a single event  argument
        *types: list of strings
            A list of event types, ex: "click", "data", "colors", "pointer_down"

        For the available renderer event types, see
        https://jupyter-rfb.readthedocs.io/en/stable/events.html

        All feature support events, i.e. ``graphic.features`` will give a set of
        all features that are evented

        Can also be used as a decorator.

        Example
        -------

        .. code-block:: py

            def my_handler(event):
                print(event)

            graphic.add_event_handler(my_handler, "pointer_up", "pointer_down")

        Decorator usage example:

        .. code-block:: py

            @graphic.add_event_handler("click")
            def my_handler(event):
                print(event)
        """

        decorating = not callable(args[0])
        types = args if decorating else args[1:]

        if decorating:

            def decorator(_callback):
                for g in self:
                    g.add_event_handler(_callback, *types)
                return _callback

            return decorator

        for g in self:
            g.add_event_handler(*args)

    def remove_event_handler(self, callback, *types):
        for g in self:
            g.remove_event_handler(callback, *types)

    def clear_event_handlers(self):
        for g in self:
            g.clear_event_handlers()

    def __getitem__(self, item):
        return self.graphics[item]

    def __len__(self):
        return len(self._selection)

    def __iter__(self):
        self._iter = iter(range(len(self)))
        return self

    def __next__(self) -> Graphic:
        index = next(self._iter)

        return self.graphics[index]

    def __repr__(self):
        return (
            f"{self.__class__.__name__} @ {hex(id(self))}\n"
            f"Selection of <{len(self._selection)}> {self._selection[0].__class__.__name__}"
        )


class GraphicCollection(Graphic, CollectionProperties):
    """Graphic Collection base class"""

    _child_type: type
    _indexer: type

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._features = cls._child_type._features

    def __init__(self, name: str = None, metadata: Any = None, **kwargs):
        super().__init__(name=name, metadata=metadata, **kwargs)

        # list of mem locations of the graphics
        self._graphics: list[Graphic] = list()

        self._graphics_changed: bool = True

        self._iter = None

    @property
    def graphics(self) -> np.ndarray[Graphic]:
        """The Graphics within this collection."""

        return np.asarray(self._graphics)

    def add_graphic(self, graphic: Graphic):
        """
        Add a graphic to the collection.

        Parameters
        ----------
        graphic: Graphic
            graphic to add, must be a real ``Graphic`` not a proxy

        """

        if not type(graphic) == self._child_type:
            raise TypeError(
                f"Can only add graphics of the same type to a collection.\n"
                f"You can only add {self._child_type.__name__} to a {self.__class__.__name__}, "
                f"you are trying to add a {graphic.__class__.__name__}."
            )

        self._graphics.append(graphic)

        self.world_object.add(graphic.world_object)

        self._graphics_changed = True

    def remove_graphic(self, graphic: Graphic):
        """
        Remove a graphic from the collection.

        Note: Only removes the graphic from the collection. Does not remove
        the graphic from the scene, and does not delete the graphic.

        Parameters
        ----------
        graphic: Graphic
            graphic to remove

        """

        self._graphics.remove(graphic)

        self.world_object.remove(graphic.world_object)

        self._graphics_changed = True

    def add_event_handler(self, *args):
        """
        Register an event handler.

        Parameters
        ----------
        callback: callable, the first argument
            Event handler, must accept a single event  argument
        *types: list of strings
            A list of event types, ex: "click", "data", "colors", "pointer_down"

        For the available renderer event types, see
        https://jupyter-rfb.readthedocs.io/en/stable/events.html

        All feature support events, i.e. ``graphic.features`` will give a set of
        all features that are evented

        Can also be used as a decorator.

        Example
        -------

        .. code-block:: py

            def my_handler(event):
                print(event)

            graphic.add_event_handler(my_handler, "pointer_up", "pointer_down")

        Decorator usage example:

        .. code-block:: py

            @graphic.add_event_handler("click")
            def my_handler(event):
                print(event)
        """

        return self[:].add_event_handler(*args)

    def remove_event_handler(self, callback, *types):
        """remove an event handler"""
        self[:].remove_event_handler(callback, *types)

    def clear_event_handlers(self):
        self[:].clear_event_handlers()

    def _fpl_add_plot_area_hook(self, plot_area):
        super()._fpl_add_plot_area_hook(plot_area)

        for g in self:
            g._fpl_add_plot_area_hook(plot_area)

    def _fpl_prepare_del(self):
        """
        Cleans up the graphic in preparation for __del__(), such as removing event handlers from
        plot renderer, feature event handlers, etc.

        Optionally implemented in subclasses
        """
        # clear any attached event handlers and animation functions
        self.world_object._event_handlers.clear()

        for g in self:
            g._fpl_prepare_del()

    def __getitem__(self, key) -> CollectionIndexer:
        if np.issubdtype(type(key), np.integer):
            return self.graphics[key]

        return self._indexer(selection=self.graphics[key], features=self._features)

    def __del__(self):
        # detach children
        self.world_object.clear()

        for g in self.graphics:
            g._fpl_prepare_del()
            del g

        super().__del__()

    def __len__(self):
        return len(self._graphics)

    def __iter__(self):
        self._iter = iter(range(len(self)))
        return self

    def __next__(self) -> Graphic:
        index = next(self._iter)

        return self._graphics[index]

    def __repr__(self):
        rval = super().__repr__()
        return f"{rval}\nCollection of <{len(self._graphics)}> Graphics"


class CollectionFeature:
    """Collection Feature"""

    def __init__(self, selection: np.ndarray[Graphic], feature: str):
        """
        selection: list of Graphics
            a list of the selected Graphics from the parent GraphicCollection based on the ``selection_indices``

        feature: str
            feature of Graphics in the GraphicCollection being indexed

        """

        self._selection = selection
        self._feature = feature

        self._feature_instances = [getattr(g, feature) for g in self._selection]

    def __getitem__(self, item):
        return np.stack([fi[item] for fi in self._feature_instances])

    def __setitem__(self, key, value):
        for fi in self._feature_instances:
            fi[key] = value

    def __repr__(self):
        return f"Collection feature for: <{self._feature}>"
