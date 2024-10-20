from functools import partial

import numpy as np

import pygfx


from ..graphics._features import VertexPositions, UniformColor, Thickness
from ..layouts._subplot import Subplot
from ..graphics._base import Graphic


class Cursor:
    def __init__(
            self,
            parent: Graphic = None,
            children: list[Graphic] = None,
            size: float = 10.0,
            style: str = "+",
            color: str | tuple | np.ndarray = "r",
            alpha: float = 0.75,
            key_toggle_moveable: str = "m",
            key_add_sticky: str = "s",
    ):
        if children is None:
            children = list()

        self._children = list()

        self._callbacks = dict()

        self._pointers: dict[Graphic, pygfx.Points] = dict()
        self._sticky_pointers = dict[Graphic, list[pygfx.Points]]

        self._size = size
        self._style = style
        self._alpha = alpha
        color = np.array(pygfx.Color(color))
        color[-1] = self._alpha
        self._color = color

        # current x, y, z position of the cursor
        self._position: np.ndarray = np.array([0., 0., 0.], dtype=np.float32)

        for child in children:
            self.add(child)

        self._respond_pointer_move: bool = True

    def _make_pointer(self, offset) -> pygfx.WorldObject:
        geo = pygfx.Geometry(positions=self.position[None, :])
        material = pygfx.PointsMarkerMaterial(
            size=self.size,
            size_space="world",
            color=self._color,
            marker=self.style
        )
        wo = pygfx.Points(
            geometry=geo,
            material=material
        )

        # set z above
        offset = offset.copy()
        offset[-1] += 1
        wo.world.position = offset

        return wo

    @property
    def position(self) -> np.ndarray:
        return self._position

    @position.setter
    def position(self, pos: tuple | list | np.ndarray):
        pos = np.asarray(pos)
        if not pos.shape == (3,):
            raise ValueError

        self._position = pos

        for child in self.children:
            wo = self._pointers[child]
            pos = self.position.copy()
            pos[-1] = child.offset[-1] + 1.
            wo.geometry.positions.data[:] = pos
            wo.geometry.positions.update_range()

    @property
    def children(self) -> tuple[Graphic, ...]:
        return tuple(self._children)

    @property
    def size(self) -> float:
        return self._size

    @property
    def style(self) -> str:
        return self._style

    def add(self, child: Graphic):
        if child in self.children:
            raise ValueError("child already registered")

        callback = partial(self._pointer_moved, child)
        self._callbacks[child] = callback

        pointer = self._make_pointer(child.offset)

        self._pointers[child] = pointer

        child.add_event_handler(callback, "pointer_move")
        child._fpl_plot_area.scene.add(pointer)

        self._children.append(child)

    def remove(self, child: Graphic):
        if child not in self.children:
            raise ValueError

        pointer = self._pointers.pop(child)

        callback = self._callbacks.pop(child)

        child.remove_event_handler(callback, "pointer_move")

        child._fpl_plot_area.scene.remove(pointer)

        self._children.remove(child)

    def _adjust_offsets(self, ev):
        graphic = ev.graphic
        offset = graphic.offset
        offset[-1] += 1

        self._pointers[graphic].world.position = offset

    def _pointer_moved(self, child: Graphic, ev: pygfx.PointerEvent):
        if not self._respond_pointer_move:
            return

        world_pos = child._fpl_plot_area.map_screen_to_world(ev)

        world_pos -= child.offset

        self.position = world_pos

    def _add_sticky_pointer(self):
        pass

    def _toggle_respond_pointer_move(self):
        self._respond_pointer_move = not self._respond_pointer_move
