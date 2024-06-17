from collections import defaultdict
from functools import partial
from typing import Any, Literal, TypeAlias
import weakref

import numpy as np
import pylinalg as la
from wgpu.gui.base import log_exception

import pygfx

from ._features import (
    BufferManager,
    Deleted,
    Name,
    Offset,
    Rotation,
    Visible,
)

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
    _features = {}

    def __init_subclass__(cls, **kwargs):
        # set the type of the graphic in lower case like "image", "line_collection", etc.
        cls.type = (
            cls.__name__.lower()
            .replace("graphic", "")
            .replace("collection", "_collection")
            .replace("stack", "_stack")
        )

        # set of all features
        cls._features = {
            *cls._features,
            "name",
            "offset",
            "rotation",
            "visible",
            "deleted",
        }
        super().__init_subclass__(**kwargs)

    def __init__(
        self,
        name: str = None,
        offset: np.ndarray | list | tuple = (0.0, 0.0, 0.0),
        rotation: np.ndarray | list | tuple = (0.0, 0.0, 0.0, 1.0),
        visible: bool = True,
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
        self._visible = Visible(visible)
        self._block_events = False

    @property
    def supported_events(self) -> tuple[str]:
        """events supported by this graphic"""
        return (*tuple(self._features), *PYGFX_EVENTS)

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

    @property
    def block_events(self) -> bool:
        """Used to block events for a graphic and prevent recursion."""
        return self._block_events

    @block_events.setter
    def block_events(self, value: bool):
        self._block_events = value

    @property
    def world_object(self) -> pygfx.WorldObject:
        """Associated pygfx WorldObject. Always returns a proxy, real object cannot be accessed directly."""
        # We use weakref to simplify garbage collection
        return weakref.proxy(WORLD_OBJECTS[self._fpl_address])

    def _set_world_object(self, wo: pygfx.WorldObject):
        WORLD_OBJECTS[self._fpl_address] = wo

        self.world_object.visible = self.visible

        # set offset if it's not (0., 0., 0.)
        if not all(self.world_object.world.position == self.offset):
            self.offset = self.offset

        # set rotation if it's not (0., 0., 0., 1.)
        if not all(self.world_object.world.rotation == self.rotation):
            self.rotation = self.rotation

    def unshare_property(self, feature: str):
        raise NotImplementedError

    def share_property(self, feature: BufferManager):
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

        unsupported_events = [t for t in types if t not in self.supported_events]

        if len(unsupported_events) > 0:
            raise TypeError(
                f"unsupported events passed: {unsupported_events} for {self.__class__.__name__}\n"
                f"`graphic.events` will return a tuple of supported events"
            )

        def decorator(_callback):
            _callback_wrapper = partial(
                self._handle_event, _callback
            )  # adds graphic instance as attribute and other things

            for t in types:
                # add to our record
                self._event_handlers[t].add(_callback)

                if t in self._features:
                    # fpl feature event
                    feature = getattr(self, f"_{t}")
                    feature.add_event_handler(_callback_wrapper)
                else:
                    # wrap pygfx event
                    self.world_object._event_handlers[t].add(_callback_wrapper)

                # keep track of the partial too
                self._event_handler_wrappers[t].add((_callback, _callback_wrapper))
            return _callback

        if decorating:
            return decorator

        return decorator(callback)

    def clear_event_handlers(self):
        """clear all event handlers added to this graphic"""
        for ev, handlers in self.event_handlers:
            handlers = list(handlers)
            for h in handlers:
                self.remove_event_handler(h, ev)

    def _handle_event(self, callback, event: pygfx.Event):
        """Wrap pygfx event to add graphic to pick_info"""
        event.graphic = self

        if self.block_events:
            return

        if event.type in self._features:
            # for feature events
            event._target = self.world_object

        if isinstance(event, pygfx.PointerEvent):
            # map from screen to world space and data space
            world_xy = self._plot_area.map_screen_to_world(event)

            # subtract offset to map to data
            data_xy = world_xy - self.offset

            # append attributes
            event.x_world, event.y_world = world_xy[:2]
            event.x_data, event.y_data = data_xy[:2]

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
                raise KeyError(
                    f"event type: {t} with callback: {callback} is not registered"
                )

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
        # remove event handlers
        self.clear_event_handlers()

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

        for n in self._features:
            fea = getattr(self, f"_{n}")
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
