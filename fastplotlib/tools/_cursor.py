from functools import partial
from typing import Literal, Sequence, Callable

import numpy as np
import pygfx

from ..layouts import Subplot
from ..utils import RenderQueue


class Cursor:
    def __init__(
        self,
        mode: Literal["crosshair", "marker"] = "crosshair",
        size: float = 1.0,  # in screen space
        color: str | Sequence[float] | pygfx.Color | np.ndarray = "w",
        marker: str = "+",
        edge_color: str | Sequence[float] | pygfx.Color | np.ndarray = "k",
        edge_width: float = 0.5,
        alpha: float = 0.7,
        size_space: Literal["screen", "world"] = "screen",
    ):
        """
        A cursor that indicates the same position in world-space across subplots.

        Parameters
        ----------
        mode: "crosshair" | "marker"
            cursor mode

        size: float, default 1.0
            * if ``mode`` == 'crosshair', this is the crosshair line thickness
            * if ``mode`` == 'marker', it's the size of the marker

            You probably want to use ``size > 5`` if ``mode`` is 'marker' and ``size_space`` is ``screen``

        color: str | Sequence[float] | pygfx.Color | np.ndarray, default "r"
            color of the marker

        marker: str, default "+"
            marker shape, used if mode == 'marker'

        edge_color: str | Sequence[float] | pygfx.Color | np.ndarray, default "k"
            marker edge color, used if mode == 'marker'

        edge_width: float, default 0.5
            marker edge widget, used if mode == 'marker'

        alpha: float, default 0.7
            alpha (transparency) of the cursor

        size_space: "screen" | "world", default "screen"
            size space of the cursor, if "screen" the ``size`` is exact screen pixels.
            if "world" the ``size`` is in world-space

        """

        self._cursors: dict[Subplot, [pygfx.Points | pygfx.Group[pygfx.Line]]] = dict()
        self._transforms: dict[Subplot, [Callable | None]] = dict()

        self._mode = None
        self.mode = mode
        self.size = size
        self.color = color
        self.marker = marker
        self.edge_color = edge_color
        self.edge_width = edge_width
        self.alpha = alpha
        self.size_space = size_space

        self._pause = False

        self._position = [0, 0]

    @property
    def mode(self) -> Literal["crosshair", "marker"]:
        return self._mode

    @mode.setter
    def mode(self, mode: Literal["crosshair", "marker"]):
        if not (mode == "crosshair" or mode == "marker"):
            raise ValueError(
                f"mode must be one of: 'crosshair' | 'marker', you passed: {mode}"
            )

        if mode == self.mode:
            return

        # mode has changed, clear and create new world objects
        subplots = list(self._cursors.keys())

        self.clear()

        for subplot in subplots:
            self.add_subplot(subplot)

        self._mode = mode

    @property
    def size(self) -> float:
        return self._size

    @size.setter
    def size(self, new_size: float):
        for c in self._cursors.values():
            if self.mode == "marker":
                c.material.size = new_size
            elif self.mode == "crosshair":
                h, v = c.children
                h.material.thickness = new_size
                v.material.thickness = new_size

        self._size = new_size

    @property
    def size_space(self) -> Literal["screen", "world"]:
        return self._size_space

    @size_space.setter
    def size_space(self, space: Literal["screen", "world"]):
        if space not in ["screen", "world", "model"]:
            raise ValueError(
                f"valid `size_space` is one of: 'screen' | 'world'. You passed: {space}"
            )

        for c in self._cursors.values():
            if self.mode == "marker":
                c.material.size_space = space

            elif self.mode == "crosshair":
                h, v = c.children
                h.material.thickness_space = space
                v.material.thickness_space = space

        self._size_space = space

    @property
    def color(self) -> pygfx.Color:
        return self._color

    @color.setter
    def color(self, new_color):
        new_color = pygfx.Color(new_color)

        for c in self._cursors.values():
            c.material.color = new_color

        self._color = new_color

    @property
    def marker(self) -> str:
        return self._marker

    @marker.setter
    def marker(self, new_marker: str):
        if self.mode == "marker":
            for c in self._cursors.values():
                c.material.marker = new_marker

        self._marker = new_marker

    @property
    def edge_color(self) -> pygfx.Color:
        return self._edge_color

    @edge_color.setter
    def edge_color(self, new_color: str | Sequence | np.ndarray | pygfx.Color):
        new_color = pygfx.Color(new_color)

        if self.mode == "marker":
            for c in self._cursors.values():
                c.material.edge_color = new_color

        self._edge_color = new_color

    @property
    def edge_width(self) -> float:
        return self._edge_width

    @edge_width.setter
    def edge_width(self, new_width: float):
        if self.mode == "marker":
            for c in self._cursors.values():
                c.material.edge_width = new_width

        self._edge_width = new_width

    @property
    def alpha(self) -> float:
        return self._alpha

    @alpha.setter
    def alpha(self, value: float):
        for c in self._cursors.values():
            c.material.opacity = value

        self._alpha = value

    @property
    def pause(self) -> bool:
        return self._pause

    @pause.setter
    def pause(self, pause: bool):
        self._pause = bool(pause)

    @property
    def position(self) -> tuple[float, float]:
        """x, y position in world space"""
        return tuple(self._position)

    @position.setter
    def position(self, pos: tuple[float, float]):
        for subplot, cursor in self._cursors.items():
            if self._transforms[subplot] is not None:
                pos_transformed = self._transforms[subplot](pos)
            else:
                pos_transformed = pos

            if self.mode == "marker":
                cursor.geometry.positions.data[0, :-1] = pos_transformed
                cursor.geometry.positions.update_full()

            elif self.mode == "crosshair":
                line_h, line_v = cursor.children

                # set x vals for horizontal line
                line_h.geometry.positions.data[0, 0] = pos_transformed[0] - 1
                line_h.geometry.positions.data[1, 0] = pos[0] + 1

                # set y value
                line_h.geometry.positions.data[:, 1] = pos_transformed[1]

                line_h.geometry.positions.update_full()

                # set y vals for vertical line
                line_v.geometry.positions.data[0, 1] = pos_transformed[1] - 1
                line_v.geometry.positions.data[1, 1] = pos_transformed[1] + 1

                # set x value
                line_v.geometry.positions.data[:, 0] = pos_transformed[0]

                line_v.geometry.positions.update_full()

            # set tooltip using pick info if a graphic is at this position
            # for now we just set z = 1
            screen_pos = subplot.map_world_to_screen((*pos_transformed, 1))
            pick_info = subplot.get_pick_info(screen_pos)

            self._position[:] = pos_transformed

            if pick_info is not None:
                graphic = pick_info["graphic"]
                if graphic._fpl_support_tooltip:  # some graphics don't support tooltips, ex: Text
                    if graphic.tooltip_format is not None:
                        # custom formatter
                        info = graphic.tooltip_format
                    else:
                        # default formatter for this graphic
                        info = graphic.format_pick_info(pick_info)

                    subplot.tooltip.display(screen_pos, info)
                    continue

            # tooltip cleared if none of the above condiitionals reached the tooltip display call
            subplot.tooltip.clear()

    def add_subplot(self, subplot: Subplot, transform: Callable | None = None):
        """add this cursor to a subplot, with an optional position transform function"""
        if subplot in self._cursors.keys():
            raise KeyError(f"The given subplot has already been added to this cursor")

        if (not callable(transform)) and (transform is not None):
            raise TypeError(f"`transform` must be a callable or `None`, you passed: {transform}")

        if self.mode == "marker":
            cursor = self._create_marker()

        elif self.mode == "crosshair":
            cursor = self._create_crosshair()

        subplot.scene.add(cursor)
        subplot.renderer.add_event_handler(
            partial(self._pointer_moved, subplot), "pointer_move"
        )

        self._cursors[subplot] = cursor
        self._transforms[subplot] = transform

        # let cursor manage tooltips
        subplot.renderer.remove_event_handler(subplot._fpl_set_tooltip, "pointer_move")

    def remove_subplot(self, subplot: Subplot):
        """remove cursor from subplot"""
        if subplot not in self._cursors.keys():
            raise KeyError("cursor not in given supblot")

        subplot.scene.remove(self._cursors.pop(subplot))

        # give back tooltip control to the subplot
        subplot.renderer.add_event_handler(subplot._fpl_set_tooltip, "pointer_move")

    def clear(self):
        """remove from all subplots"""
        for subplot in self._cursors.keys():
            self.remove_subplot(subplot)

    def _create_marker(self) -> pygfx.Points:
        point = pygfx.Points(
            pygfx.Geometry(positions=np.array([[*self.position, 0]], dtype=np.float32)),
            pygfx.PointsMarkerMaterial(
                marker=self.marker,
                size=self.size,
                size_space=self.size_space,
                color=self.color,
                edge_color=self.edge_color,
                edge_width=self.edge_width,
                opacity=self.alpha,
                alpha_mode="blend",
                render_queue=RenderQueue.selector,
                depth_test=False,
                depth_write=False,
                pick_write=False,
            ),
        )

        return point

    def _create_crosshair(self) -> pygfx.Group:
        x, y = self.position
        line_h_data = np.array(
            [
                [x - 1, y, 0],
                [x + 1, y, 0],
            ],
            dtype=np.float32,
        )

        line_v_data = np.array(
            [
                [x, y - 1, 0],
                [x, y + 1, 0],
            ],
            dtype=np.float32,
        )

        line_h = pygfx.Line(
            geometry=pygfx.Geometry(positions=line_h_data),
            material=pygfx.LineInfiniteSegmentMaterial(
                thickness=self.size,
                thickness_space=self.size_space,
                color=self.color,
                opacity=self.alpha,
                alpha_mode="blend",
                aa=True,
                render_queue=RenderQueue.selector,
                depth_test=False,
                depth_write=False,
                pick_write=False,
            ),
        )

        line_v = pygfx.Line(
            geometry=pygfx.Geometry(positions=line_v_data),
            material=pygfx.LineInfiniteSegmentMaterial(
                thickness=self.size,
                thickness_space=self.size_space,
                color=self.color,
                opacity=self.alpha,
                alpha_mode="blend",
                aa=True,
                render_queue=RenderQueue.selector,
                depth_test=False,
                depth_write=False,
                pick_write=False,
            ),
        )

        lines = pygfx.Group()
        lines.add(line_h, line_v)

        return lines

    def _pointer_moved(self, subplot, ev: pygfx.PointerEvent):
        if self.pause:
            return

        pos = subplot.map_screen_to_world(ev)

        if pos is None:
            return

        self.position = pos[:-1]
