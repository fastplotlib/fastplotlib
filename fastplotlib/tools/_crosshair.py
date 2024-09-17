from functools import partial

import numpy as np

import pygfx


from ..graphics._features import VertexPositions, UniformColor, Thickness
from ..layouts._subplot import Subplot


class CrosshairTool:
    def __init__(
            self,
            subplots: Subplot | list[Subplot],
            thickness: float = 1.0,
            style: str = "+",
            color: str | tuple | np.ndarray = "w",
            alpha: float = 0.5,
    ):
        self._subplots = list()
        self._subplot_callbacks = dict()

        self._world_objects: list[pygfx.Line] = list()

        self._thickness = thickness
        self._style = style
        self._color = color
        self._alpha = alpha

    @property
    def subplots(self) -> tuple[Subplot, ...]:
        return tuple(self._subplots)

    @property
    def thickness(self) -> float:
        return self._thickness

    @property
    def style(self) -> str:
        return self._style

    def add_subplot(self, subplot: Subplot):
        if subplot.camera.fov > 0:
            # TODO: worry about perspective projections later
            raise TypeError("Crosshair currently only supported for Orthographic projections")

        if subplot in self.subplots:
            raise ValueError("subplot already registered")

        if len(self._world_objects) < 1:
            # get center of subplot to initialize crosshair lines

            self._hline = pygfx.Line(
                geometry=pygfx.Geometry
            )

        callback = partial(self._pointer_moved, subplot)
        self._subplot_callbacks[subplot] = callback
        subplot.renderer.add_event_handler(callback, "pointer_move")

    def remove_subplot(self, subplot: Subplot):
        if subplot not in self.subplots:
            raise ValueError

        callback = self._subplot_callbacks.pop(subplot)
        subplot.renderer.remove_event_handler(callback)

        self._subplots.remove(subplot)

    def set_intersection(self, pos: tuple[float, float, float]):
        """set intersection in world space"""
        pass

    def _pointer_moved(self, subplot: Subplot, ev: pygfx.PointerEvent):
        world_pos = subplot.map_screen_to_world(ev)

        # get bbox of subplot, code taken from axes
        # TODO: perhaps this should be moved to utils or something?
        xpos, ypos, width, height = subplot.get_rect()
        # orthographic projection, get ranges using inverse

        # get range of screen space by getting the corners
        xmin, xmax = xpos, xpos + width
        ymin, ymax = ypos + height, ypos

        min_vals = subplot.map_screen_to_world((xmin, ymin))
        max_vals = subplot.map_screen_to_world((xmax, ymax))

        if min_vals is None or max_vals is None:
            return

        world_xmin, world_ymin, _ = min_vals
        world_xmax, world_ymax, _ = max_vals

        # world range to set endpoints of crosshair

