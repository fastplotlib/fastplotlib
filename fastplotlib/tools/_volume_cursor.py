from functools import partial
from typing import Callable, Literal, Sequence

import numpy as np
import pygfx

from ..graphics import ImageVolumeGraphic
from ..layouts import Subplot
from ..utils import RenderQueue

AXES = ("x", "y", "z")
NORMALS = {"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}
DEFAULT_COLORS = {"x": "#e57373", "y": "#ffb74d", "z": "#4fc3f7"}


class VolumeCursor:
    def __init__(
        self,
        position: Sequence[float] = (0.0, 0.0, 0.0),
        colors: dict[str, str | Sequence[float] | pygfx.Color] = None,
        thickness: float = 1.5,
        alpha: float = 0.8,
        click_slop: float = 4.0,
    ):
        """
        A 3D crosshair: one point in world space shown across 2D slice views and in 3D volumes.

        Each 2D subplot shows two of the three world axes and gets one line per axis. Each volume gets
        three orthogonal slices through the point, outlined in the axis colors. Clicking a 2D subplot
        moves the point.

        Parameters
        ----------
        position: (float, float, float), default (0, 0, 0)
            initial (x, y, z) position in world space

        colors: dict, optional
            {"x": color, "y": color, "z": color}, the color of each axis's lines and slice outline

        thickness: float, default 1.5
            line thickness in screen pixels

        alpha: float, default 0.8
            line alpha

        click_slop: float, default 4.0
            a pointer press and release closer than this many screen pixels is a click and moves the point,
            a longer drag is left to the camera controller

        """
        self._colors = {
            axis: pygfx.Color((colors or DEFAULT_COLORS).get(axis, DEFAULT_COLORS[axis]))
            for axis in AXES
        }
        self._thickness = thickness
        self._alpha = alpha
        self._click_slop = click_slop

        # subplot -> (axes shown on its x and y, group of the two lines, pointer handler)
        self._subplots: dict[Subplot, tuple[tuple[str, str], pygfx.Group, Callable]] = dict()
        # volume graphic -> {axis: slice graphic}, {axis: outline}
        self._volumes: dict[ImageVolumeGraphic, tuple[dict, dict]] = dict()

        self._handlers: list[Callable] = list()
        # subplot -> screen position of the last pointer press inside it
        self._press: dict[Subplot, tuple[float, float] | None] = dict()
        self._enabled = True
        self._visible = True
        self._position = np.asarray(position, dtype=np.float32)

    @property
    def position(self) -> tuple[float, float, float]:
        """Get or set the (x, y, z) position in world space"""
        return tuple(float(v) for v in self._position)

    @position.setter
    def position(self, pos: Sequence[float]):
        pos = np.asarray(pos, dtype=np.float32)
        if np.array_equal(pos, self._position):
            return

        self._position[:] = pos
        self._update()

        for handler in self._handlers:
            handler(self.position)

    @property
    def enabled(self) -> bool:
        """If False, clicks do not move the cursor"""
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = bool(value)

    @property
    def visible(self) -> bool:
        """Get or set the visibility of the lines, slices and outlines"""
        return self._visible

    @visible.setter
    def visible(self, value: bool):
        self._visible = bool(value)
        for _axes, lines, _handler in self._subplots.values():
            lines.visible = self._visible
        for slices, outlines in self._volumes.values():
            for graphic in slices.values():
                graphic.visible = self._visible
            for outline in outlines.values():
                outline.visible = self._visible

    @property
    def colors(self) -> dict[str, pygfx.Color]:
        """The color of each axis"""
        return dict(self._colors)

    def slices(self, volume: ImageVolumeGraphic) -> dict[str, ImageVolumeGraphic]:
        """The {axis: slice graphic} added for ``volume``"""
        return dict(self._volumes[volume][0])

    def add_event_handler(self, handler: Callable[[tuple[float, float, float]], None]) -> Callable:
        """
        Call ``handler(position)`` whenever the position changes. Can be used as a decorator.

        Parameters
        ----------
        handler: Callable
            called with the new (x, y, z) world position

        Returns
        -------
        Callable
            ``handler``

        """
        self._handlers.append(handler)
        return handler

    def remove_event_handler(self, handler: Callable):
        """remove an event handler"""
        self._handlers.remove(handler)

    def add_subplot(self, subplot: Subplot, axes: tuple[str, str]):
        """
        Show the cursor on a 2D subplot.

        Parameters
        ----------
        subplot: Subplot
            subplot to add

        axes: (str, str)
            the world axes the subplot's x and y show, for example ("x", "z") for an XZ view. The subplot's
            graphics must be placed in those axes' world units, i.e. scaled the same as the volumes.

        """
        if subplot in self._subplots:
            raise KeyError("The given subplot has already been added to this cursor")

        axes = tuple(axes)
        if len(axes) != 2 or len(set(axes)) != 2 or not set(axes) <= set(AXES):
            raise ValueError(f"`axes` must be two different axes of 'x', 'y', 'z', you passed: {axes}")

        # vertical line at the position along the subplot's x, horizontal line along its y
        lines = pygfx.Group()
        lines.add(
            self._create_line(direction=(0, 1), color=self._colors[axes[0]]),
            self._create_line(direction=(1, 0), color=self._colors[axes[1]]),
        )
        lines.visible = self._visible
        subplot.scene.add(lines)

        handler = partial(self._pointer_event, subplot)
        subplot.renderer.add_event_handler(handler, "pointer_down", "pointer_up")

        self._subplots[subplot] = (axes, lines, handler)
        self._update()

    def remove_subplot(self, subplot: Subplot):
        """remove a 2D subplot"""
        _axes, lines, handler = self._subplots.pop(subplot)
        subplot.scene.remove(lines)
        subplot.renderer.remove_event_handler(handler, "pointer_down", "pointer_up")

    def add_volume(self, volume: ImageVolumeGraphic):
        """
        Show three orthogonal slices through the cursor inside a volume, each outlined in its axis color.

        The slices share the volume's data buffer and follow its ``vmin``, ``vmax`` and ``cmap``. The volume
        stops writing depth so the slices inside it stay visible.

        Parameters
        ----------
        volume: ImageVolumeGraphic
            volume to add, it must already be in a subplot

        """
        if volume in self._volumes:
            raise KeyError("The given volume has already been added to this cursor")

        subplot = volume._plot_area
        local = volume.world_object.local

        for tile in volume.world_object.children:
            tile.material.depth_write = False

        slices, outlines = dict(), dict()
        for axis in AXES:
            graphic = subplot.add_image_volume(
                volume.data,
                mode="slice",
                cmap=volume.cmap,
                vmin=volume.vmin,
                vmax=volume.vmax,
                name=f"{volume.name or 'volume'}_cursor_slice_{axis}",
            )
            graphic.world_object.local.position = local.position
            graphic.world_object.local.rotation = local.rotation
            graphic.world_object.local.scale = local.scale
            graphic.visible = self._visible
            # draw after the volume, whose max projection no longer fills the depth buffer
            for tile in graphic.world_object.children:
                tile.render_order = 1
            slices[axis] = graphic

            outline = self._create_outline(color=self._colors[axis])
            outline.visible = self._visible
            subplot.scene.add(outline)
            outlines[axis] = outline

        for feature in ("vmin", "vmax", "cmap"):
            volume.add_event_handler(partial(self._volume_feature_changed, slices), feature)

        self._volumes[volume] = (slices, outlines)
        self._update()

    def remove_volume(self, volume: ImageVolumeGraphic):
        """remove a volume and delete its slices"""
        slices, outlines = self._volumes.pop(volume)
        subplot = volume._plot_area
        for graphic in slices.values():
            subplot.delete_graphic(graphic)
        for outline in outlines.values():
            subplot.scene.remove(outline)
        for tile in volume.world_object.children:
            tile.material.depth_write = True

    def clear(self):
        """remove all subplots and volumes"""
        for subplot in list(self._subplots):
            self.remove_subplot(subplot)
        for volume in list(self._volumes):
            self.remove_volume(volume)

    def _create_line(self, direction: tuple[int, int], color: pygfx.Color) -> pygfx.Line:
        # an infinite line through the origin along ``direction``, moved by its local position
        positions = np.zeros((2, 3), dtype=np.float32)
        positions[0, :2] = np.negative(direction)
        positions[1, :2] = direction
        return pygfx.Line(
            geometry=pygfx.Geometry(positions=positions),
            material=pygfx.LineInfiniteSegmentMaterial(
                thickness=self._thickness,
                color=color,
                opacity=self._alpha,
                alpha_mode="blend",
                aa=True,
                render_queue=RenderQueue.selector,
                depth_test=False,
                depth_write=False,
                pick_write=False,
            ),
        )

    def _create_outline(self, color: pygfx.Color) -> pygfx.Line:
        return pygfx.Line(
            geometry=pygfx.Geometry(positions=np.zeros((5, 3), dtype=np.float32)),
            material=pygfx.LineMaterial(
                thickness=self._thickness + 0.5,
                color=color,
                opacity=self._alpha,
                alpha_mode="blend",
                aa=True,
                pick_write=False,
            ),
        )

    def _update(self):
        position = dict(zip(AXES, self._position))

        for axes, lines, _handler in self._subplots.values():
            line_v, line_h = lines.children
            line_v.local.x = position[axes[0]]
            line_h.local.y = position[axes[1]]

        for volume, (slices, outlines) in self._volumes.items():
            bbox = volume.world_object.get_world_bounding_box()  # [[xmin, ymin, zmin], [xmax, ymax, zmax]]
            for axis, graphic in slices.items():
                # slice planes are in world space: ax + by + cz + d = 0
                graphic.plane = (*NORMALS[axis], -position[axis])

                index = AXES.index(axis)
                a, b = (i for i in range(3) if i != index)
                corners = np.zeros((5, 3), dtype=np.float32)
                corners[:, index] = position[axis]
                corners[:, a] = bbox[[0, 1, 1, 0, 0], a]
                corners[:, b] = bbox[[0, 0, 1, 1, 0], b]
                outlines[axis].geometry.positions.data[:] = corners
                outlines[axis].geometry.positions.update_full()

    def _volume_feature_changed(self, slices: dict, ev):
        for graphic in slices.values():
            setattr(graphic, ev.type, ev.info["value"])

    def _pointer_event(self, subplot: Subplot, ev: pygfx.PointerEvent):
        if not self._enabled or ev.button != 1:
            return

        if ev.type == "pointer_down":
            inside = subplot.viewport.is_inside(ev.x, ev.y)
            self._press[subplot] = (ev.x, ev.y) if inside else None
            return

        press = self._press.pop(subplot, None)
        if press is None or abs(ev.x - press[0]) + abs(ev.y - press[1]) > self._click_slop:
            return

        world = subplot.map_screen_to_world(ev)
        if world is None:
            return

        axes = self._subplots[subplot][0]
        position = dict(zip(AXES, self._position))
        position[axes[0]], position[axes[1]] = world[0], world[1]
        self.position = [position[axis] for axis in AXES]
