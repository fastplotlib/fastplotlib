import weakref

import numpy as np

from ._base import HexStr, Graphic, PYGFX_EVENTS

# Dict that holds all collection graphics in one python instance
COLLECTION_GRAPHICS: dict[HexStr, Graphic] = dict()


class CollectionIndexer:
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
    def name(self) -> np.ndarray[str | None]:
        return np.asarray([g.name for g in self.graphics])

    @name.setter
    def name(self, values: np.ndarray[str] | list[str]):
        self._set_feature("name", values)

    @property
    def offset(self) -> np.ndarray:
        return np.stack([g.offset for g in self.graphics])

    @offset.setter
    def offset(self, values: np.ndarray | list[np.ndarray]):
        self._set_feature("offset", values)

    @property
    def rotation(self) -> np.ndarray:
        return np.stack([g.rotation for g in self.graphics])

    @rotation.setter
    def rotation(self, values: np.ndarray | list[np.ndarray]):
        self._set_feature("rotation", values)

    @property
    def visible(self) -> np.ndarray[bool]:
        return np.asarray([g.visible for g in self.graphics])

    # TODO: how to work with deleted feature in a collection

    @visible.setter
    def visible(self, values: np.ndarray[bool] | list[bool]):
        self._set_feature("visible", values)

    def _set_feature(self, feature, values):
        if not len(values) == len(self):
            raise IndexError

        for g, v in zip(self.graphics, values):
            setattr(g, feature, v)

    @property
    def graphics(self) -> np.ndarray[Graphic]:
        """Returns an array of the selected graphics. Always returns a proxy to the Graphic"""
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
                for g in self.graphics:
                    g.add_event_handler(_callback, *types)
                return _callback

            return decorator

        for g in self.graphics:
            g.add_event_handler(*args)

    def remove_event_handler(self, callback, *types):
        for g in self.graphics:
            g.remove_event_handler(callback, *types)

    def __getitem__(self, item):
        return self.graphics[item]

    def __len__(self):
        return len(self._selection)

    def __repr__(self):
        return (
            f"{self.__class__.__name__} @ {hex(id(self))}\n"
            f"Selection of <{len(self._selection)}> {self._selection[0].__class__.__name__}"
        )


class GraphicCollection(Graphic):
    """Graphic Collection base class"""

    child_type: type
    _indexer: type

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._features = cls.child_type._features

    def __init__(self, name: str = None):
        super().__init__(name)

        # list of mem locations of the graphics
        self._graphics: list[str] = list()

        self._graphics_changed: bool = True
        self._graphics_array: np.ndarray[Graphic] = None

    @property
    def graphics(self) -> np.ndarray[Graphic]:
        """The Graphics within this collection. Always returns a proxy to the Graphics."""
        if self._graphics_changed:
            proxies = [
                weakref.proxy(COLLECTION_GRAPHICS[addr]) for addr in self._graphics
            ]
            self._graphics_array = np.array(proxies)
            self._graphics_array.flags["WRITEABLE"] = False
            self._graphics_changed = False

        return self._graphics_array

    def add_graphic(self, graphic: Graphic):
        """
        Add a graphic to the collection.

        Parameters
        ----------
        graphic: Graphic
            graphic to add, must be a real ``Graphic`` not a proxy

        """

        if not type(graphic) == self.child_type:
            raise TypeError(
                f"Can only add graphics of the same type to a collection.\n"
                f"You can only add {self.child_type.__name__} to a {self.__class__.__name__}, "
                f"you are trying to add a {graphic.__class__.__name__}."
            )

        addr = graphic._fpl_address
        COLLECTION_GRAPHICS[addr] = graphic

        self._graphics.append(addr)

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

        self._graphics.remove(graphic._fpl_address)

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
        self[:].remove_event_handler(callback, *types)

    def __getitem__(self, key) -> CollectionIndexer:
        return self._indexer(selection=self.graphics[key], features=self._features)

    def __del__(self):
        self.world_object.clear()

        for addr in self._graphics:
            del COLLECTION_GRAPHICS[addr]

        super().__del__()

    def __len__(self):
        return len(self._graphics)

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
        return [fi[item] for fi in self._feature_instances]

    def __setitem__(self, key, value):
        for fi in self._feature_instances:
            fi[key] = value

    def __repr__(self):
        return f"Collection feature for: <{self._feature}>"
