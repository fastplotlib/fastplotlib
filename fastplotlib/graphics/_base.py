from collections import defaultdict
from functools import partial
from typing import Any, Literal, TypeAlias
import weakref
from warnings import warn
from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np
import pylinalg as la
from wgpu.gui.base import log_exception

import pygfx

from ._features import GraphicFeature, BufferManager, Deleted, VertexPositions, VertexColors, VertexCmap, PointsSizesFeature, Name, Offset, Rotation, Visible, UniformColor

HexStr: TypeAlias = str

# dict that holds all world objects for a given python kernel/session
# Graphic objects only use proxies to WorldObjects
WORLD_OBJECTS: dict[HexStr, pygfx.WorldObject] = dict()  #: {hex id str: WorldObject}


PYGFX_EVENTS = [
    "key_down",
    "key_up",
    "pointer_down",
    "pointer_move",
    "pointer_up",
    "pointer_enter",
    "pointer_leave",
    "click",
    "double_click",
    "wheel",
    "close",
    "resize",
]


class Graphic:
    features = {}

    @property
    def name(self) -> str | None:
        """Graphic name"""
        return self._name.value

    @name.setter
    def name(self, value: str):
        self._name.set_value(self, value)

    @property
    def offset(self) -> np.ndarray:
        """Offset position of the graphic, array: [x, y, z]"""
        return self._offset.value

    @offset.setter
    def offset(self, value: np.ndarray | list | tuple):
        self._offset.set_value(self, value)

    @property
    def rotation(self) -> np.ndarray:
        """Orientation of the graphic as a quaternion"""
        return self._rotation.value

    @rotation.setter
    def rotation(self, value: np.ndarray | list | tuple):
        self._rotation.set_value(self, value)

    @property
    def visible(self) -> bool:
        """Whether the graphic is visible"""
        return self._visible.value

    @visible.setter
    def visible(self, value: bool):
        self._visible.set_value(self, value)

    @property
    def deleted(self) -> bool:
        """used to emit an event after the graphic is deleted"""
        return self._deleted.value

    @deleted.setter
    def deleted(self, value: bool):
        self._deleted.set_value(self, value)

    def __init_subclass__(cls, **kwargs):
        # set the type of the graphic in lower case like "image", "line_collection", etc.
        cls.type = (
            cls.__name__.lower()
            .replace("graphic", "")
            .replace("collection", "_collection")
            .replace("stack", "_stack")
        )

        # set of all features
        cls.features = {*cls.features, "name", "offset", "rotation", "visible", "deleted"}
        super().__init_subclass__(**kwargs)

    def __init__(
        self,
        name: str = None,
        offset: np.ndarray | list | tuple = (0., 0., 0.),
        rotation: np.ndarray | list | tuple = (0., 0., 0., 1.),
        metadata: Any = None,
    ):
        """

        Parameters
        ----------
        name: str, optional
            name this graphic to use it as a key to access from the plot

        offset: (float, float, float), default (0., 0., 0.)
            (x, y, z) vector to offset this graphic from the origin

        rotation: (float, float, float, float), default (0, 0, 0, 1)
            rotation quaternion

        metadata: Any, optional
            metadata attached to this Graphic, this is for the user to manage

        """
        if (name is not None) and (not isinstance(name, str)):
            raise TypeError("Graphic `name` must be of type <str>")

        self.metadata = metadata
        self.registered_callbacks = dict()

        # store hex id str of Graphic instance mem location
        self._fpl_address: HexStr = hex(id(self))

        self._plot_area = None

        # event handlers
        self._event_handlers = defaultdict(set)

        # maps callbacks to their partials
        self._event_handler_wrappers = defaultdict(set)

        # all the common features
        self._name = Name(name)
        self._deleted = Deleted(False)
        self._rotation = Rotation(rotation)
        self._offset = Offset(offset)
        self._visible = Visible(True)

    @property
    def world_object(self) -> pygfx.WorldObject:
        """Associated pygfx WorldObject. Always returns a proxy, real object cannot be accessed directly."""
        # We use weakref to simplify garbage collection
        return weakref.proxy(WORLD_OBJECTS[self._fpl_address])

    def _set_world_object(self, wo: pygfx.WorldObject):
        WORLD_OBJECTS[self._fpl_address] = wo

        # set offset if it's not (0., 0., 0.)
        if not all(self.world_object.world.position == self.offset):
            self.offset = self.offset

        # set rotation if it's not (0., 0., 0., 1.)
        if not all(self.world_object.world.rotation == self.rotation):
            self.rotation = self.rotation

    def detach_feature(self, feature: str):
        raise NotImplementedError

    def attach_feature(self, feature: BufferManager):
        raise NotImplementedError

    @property
    def event_handlers(self) -> list[tuple[str, callable, ...]]:
        """
        Registered event handlers. Read-only use ``add_event_handler()``
        and ``remove_event_handler()`` to manage callbacks
        """
        return list(self._event_handlers.items())

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
        callback = None if decorating else args[0]
        types = args if decorating else args[1:]

        def decorator(_callback):
            _callback_injector = partial(self._handle_event, _callback)  # adds graphic instance as attribute

            for t in types:
                # add to our record
                self._event_handlers[t].add(_callback)

                if t in self.features:
                    # fpl feature event
                    feature = getattr(self, f"_{t}")
                    feature.add_event_handler(_callback_injector)
                else:
                    # wrap pygfx event
                    self.world_object._event_handlers[t].add(_callback_injector)

                # keep track of the partial too
                self._event_handler_wrappers[t].add((_callback, _callback_injector))
            return _callback

        if decorating:
            return decorator

        return decorator(callback)

    def _handle_event(self, callback, event: pygfx.Event):
        """Wrap pygfx event to add graphic to pick_info"""
        event.graphic = self

        if event.type in self.features:
            # for feature events
            event._target = self.world_object

        with log_exception(f"Error during handling {event.type} event"):
            callback(event)

    def remove_event_handler(self, callback, *types):
        # remove from our record first
        for t in types:
            for wrapper_map in self._event_handler_wrappers[t]:
                # TODO: not sure if we can handle this mapping in a better way
                if wrapper_map[0] == callback:
                    wrapper = wrapper_map[1]
                    self._event_handler_wrappers[t].remove(wrapper_map)
                    break
            else:
                raise KeyError(f"event type: {t} with callback: {callback} is not registered")

            self._event_handlers[t].remove(callback)
            # remove callback wrapper from world object if pygfx event
            if t in PYGFX_EVENTS:
                print("pygfx event")
                print(wrapper)
                self.world_object.remove_event_handler(wrapper, t)
            else:
                feature = getattr(self, f"_{t}")
                feature.remove_event_handler(wrapper)

    def _fpl_add_plot_area_hook(self, plot_area):
        self._plot_area = plot_area

    def __repr__(self):
        rval = f"{self.__class__.__name__} @ {hex(id(self))}"
        if self.name is not None:
            return f"'{self.name}': {rval}"
        else:
            return rval

    def __eq__(self, other):
        # This is necessary because we use Graphics as weakref proxies
        if not isinstance(other, Graphic):
            raise TypeError("`==` operator is only valid between two Graphics")

        if self._fpl_address == other._fpl_address:
            return True

        return False

    def _fpl_cleanup(self):
        """
        Cleans up the graphic in preparation for __del__(), such as removing event handlers from
        plot renderer, feature event handlers, etc.

        Optionally implemented in subclasses
        """
        # clear any attached event handlers and animation functions
        for attr in dir(self):
            try:
                method = getattr(self, attr)
            except:
                continue

            if not callable(method):
                continue

            for ev_type in PYGFX_EVENTS:
                try:
                    self._plot_area.renderer.remove_event_handler(method, ev_type)
                except (KeyError, TypeError):
                    pass

            try:
                self._plot_area.remove_animation(method)
            except KeyError:
                pass

        for child in self.world_object.children:
            child._event_handlers.clear()

        self.world_object._event_handlers.clear()

        feature_names = getattr(self, "feature_events")
        for n in feature_names:
            fea = getattr(self, n)
            fea.clear_event_handlers()

    def __del__(self):
        self.deleted = True
        del WORLD_OBJECTS[self._fpl_address]

    def rotate(self, alpha: float, axis: Literal["x", "y", "z"] = "y"):
        """Rotate the Graphic with respect to the world.

        Parameters
        ----------
        alpha :
            Rotation angle in radians.
        axis :
            Rotation axis label.
        """
        if axis == "x":
            rot = la.quat_from_euler((alpha, 0), order="XY")
        elif axis == "y":
            rot = la.quat_from_euler((0, alpha), order="XY")
        elif axis == "z":
            rot = la.quat_from_euler((0, alpha), order="XZ")
        else:
            raise ValueError(
                f"`axis` must be either `x`, `y`, or `z`. `{axis}` provided instead!"
            )
        self.rotation = la.quat_mul(rot, self.rotation)


class PositionsGraphic(Graphic):
    """Base class for LineGraphic and ScatterGraphic"""

    @property
    def data(self) -> VertexPositions:
        """Get or set the vertex positions data"""
        return self._data

    @data.setter
    def data(self, value):
        self._data[:] = value

    @property
    def colors(self) -> VertexColors | pygfx.Color:
        """Get or set the colors data"""
        if isinstance(self._colors, VertexColors):
            return self._colors

        elif isinstance(self._colors, UniformColor):
            return self._colors.value

    @colors.setter
    def colors(self, value: str | np.ndarray | tuple[float] | list[float] | list[str]):
        if isinstance(self._colors, VertexColors):
            self._colors[:] = value

        elif isinstance(self._colors, UniformColor):
            self._colors.set_value(self, value)

    @property
    def cmap(self) -> VertexCmap:
        """Control cmap"""
        return self._cmap

    @cmap.setter
    def cmap(self, name: str):
        if self._cmap is None:
            raise BufferError("Cannot use cmap with uniform_colors=True")

        self._cmap[:] = name

    def __init__(
            self,
            data: Any,
            colors: str | np.ndarray | tuple[float] | list[float] | list[str] = "w",
            uniform_colors: bool = False,
            alpha: float = 1.0,
            cmap: str | VertexCmap = None,
            cmap_values: np.ndarray = None,
            isolated_buffer: bool = True,
            *args,
            **kwargs,
    ):
        if isinstance(data, VertexPositions):
            self._data = data
        else:
            self._data = VertexPositions(data, isolated_buffer=isolated_buffer)

        if cmap is not None:
            # if a cmap is specified it overrides colors argument
            if uniform_colors:
                raise TypeError(
                    "Cannot use cmap if uniform_colors=True"
                )

            if isinstance(cmap, str):
                # make colors from cmap
                if isinstance(colors, VertexColors):
                    # share buffer with existing colors instance for the cmap
                    self._colors = colors
                    self._colors._shared += 1
                else:
                    # create vertex colors buffer
                    self._colors = VertexColors("w", n_colors=self._data.value.shape[0])
                    # make cmap using vertex colors buffer
                    self._cmap = VertexCmap(
                        self._colors,
                        cmap_name=cmap,
                        cmap_values=cmap_values
                    )
            elif isinstance(cmap, VertexCmap):
                # use existing cmap instance
                self._cmap = cmap
                self._colors = cmap._vertex_colors
            else:
                raise TypeError
        else:
            # no cmap given
            if isinstance(colors, VertexColors):
                # share buffer with existing colors instance
                self._colors = colors
                self._colors._shared += 1
                # blank colormap instance
                self._cmap = VertexCmap(
                    self._colors,
                    cmap_name=None,
                    cmap_values=None
                )
            else:
                if uniform_colors:
                    self._colors = UniformColor(colors)
                    self._cmap = None
                else:
                    self._colors = VertexColors(
                        colors,
                        n_colors=self._data.value.shape[0],
                        alpha=alpha,
                    )
                    self._cmap = VertexCmap(self._colors, cmap_name=None, cmap_values=None)
                
        super().__init__(*args, **kwargs)

    def detach_feature(self, feature: str):
        if not isinstance(feature, str):
            raise TypeError

        f = getattr(self, feature)
        if f.shared == 0:
            raise BufferError("Cannot detach an independent buffer")

        if feature == "colors" and isinstance(feature, VertexColors):
            self._colors._buffer = pygfx.Buffer(self._colors.value.copy())
            self.world_object.geometry.colors = self._colors.buffer
            self._colors._shared -= 1

        elif feature == "data":
            self._data._buffer = pygfx.Buffer(self._data.value.copy())
            self.world_object.geometry.positions = self._data.buffer
            self._data._shared -= 1

        elif feature == "sizes":
            self._sizes._buffer = pygfx.Buffer(self._sizes.value.copy())
            self.world_object.geometry.positions = self._sizes.buffer
            self._sizes._shared -= 1

    def attach_feature(self, feature: VertexPositions | VertexColors | PointsSizesFeature):
        if isinstance(feature, VertexPositions):
            # TODO: check if this causes a memory leak
            self._data._shared -= 1

            self._data = feature
            self._data._shared += 1
            self.world_object.geometry.positions = self._data.buffer

        elif isinstance(feature, VertexColors):
            self._colors._shared -= 1

            self._colors = feature
            self._colors._shared += 1
            self.world_object.geometry.colors = self._colors.buffer

        elif isinstance(feature, PointsSizesFeature):
            self._sizes._shared -= 1

            self._sizes = feature
            self._sizes._shared += 1
            self.world_object.geometry.sizes = self._sizes.buffer

    def _event_handler(self, event):
        """Handles the event after it occurs when two graphic have been linked together."""
        if event.type in self.registered_callbacks.keys():
            for target_info in self.registered_callbacks[event.type]:
                if target_info.callback_function is not None:
                    # if callback_function is not None, then callback function should handle the entire event
                    target_info.callback_function(
                        source=self,
                        target=target_info.target,
                        event=event,
                        new_data=target_info.new_data,
                    )

                elif isinstance(self, GraphicCollection):
                    # if target is a GraphicCollection, then indices will be stored in collection_index
                    if event.type in self.feature_events:
                        indices = event.pick_info["collection-index"]

                    # for now we only have line collections so this works
                    else:
                        # get index of world object that made this event
                        for i, item in enumerate(self.graphics):
                            wo = WORLD_OBJECTS[item._fpl_address]
                            # we only store hex id of worldobject, but worldobject `pick_info` is always the real object
                            # so if pygfx worldobject triggers an event by itself, such as `click`, etc., this will be
                            # the real world object in the pick_info and not the proxy
                            if wo is event.pick_info["world_object"]:
                                indices = i
                    target_info.target.set_feature(
                        feature=target_info.feature,
                        new_data=target_info.new_data,
                        indices=indices,
                    )
                else:
                    # if target is a single graphic, then indices do not matter
                    target_info.target.set_feature(
                        feature=target_info.feature,
                        new_data=target_info.new_data,
                        indices=None,
                    )


# Dict that holds all collection graphics in one python instance
COLLECTION_GRAPHICS: dict[HexStr, Graphic] = dict()


class CollectionIndexer:
    """Collection Indexer"""
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

    @visible.setter
    def visible(self, values: np.ndarray[bool] | list[bool]):
        self._set_feature("visible", values)

    # TODO: how to work with deleted feature in a collection

    def _set_feature(self, feature, values):
        if not len(values) == len(self):
            raise IndexError

        for g, v in zip(self.graphics, values):
            setattr(g, feature, v)

    def __init__(
        self,
        selection: np.ndarray[Graphic],
        features: set[str]
    ):
        """

        Parameters
        ----------

        selection: np.ndarray of Graphics
            array of the selected Graphics from the parent GraphicCollection based on the ``selection_indices``

        """

        self._selection = selection
        self._features = features

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
        callback = None if decorating else args[0]
        types = args if decorating else args[1:]

        if not all(t in set(PYGFX_EVENTS).union(self._features) for t in types):
            raise KeyError(
                f"event types must be strings for a valid event from the following:\n"
                f"{PYGFX_EVENTS + list(self._features)}"
            )

        def decorator(_callback):
            for g in self.graphics:
                g.add_event_handler(_callback, types)
            return _callback

        if decorating:
            return decorator

        return decorator(callback)

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
        raise NotImplementedError("Slice graphic collection to add event handlers")

    def remove_event_handler(self, callback, *types):
        raise NotImplementedError("Slice graphic collection to remove event handlers")

    def __getitem__(self, key) -> CollectionIndexer:
        return self._indexer(
            selection=self.graphics[key],
        )

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
