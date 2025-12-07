from functools import partial
from typing import Literal

import numpy as np
import pygfx

from ..utils.enums import RenderQueue


class MeshMasks:
    """Used set the x0, x1, y0, y1 positions of the plane mesh"""

    x0 = np.array(
        [
            [False, False, False],
            [True, False, False],
            [False, False, False],
            [True, False, False],
        ]
    )

    x1 = np.array(
        [
            [True, False, False],
            [False, False, False],
            [True, False, False],
            [False, False, False],
        ]
    )

    y0 = np.array(
        [
            [False, True, False],
            [False, True, False],
            [False, False, False],
            [False, False, False],
        ]
    )

    y1 = np.array(
        [
            [False, False, False],
            [False, False, False],
            [False, True, False],
            [False, True, False],
        ]
    )


masks = MeshMasks


class TextBox:
    def __init__(self):
        # text object
        self._text = pygfx.Text(
            text="",
            font_size=12,
            screen_space=False,
            anchor="bottom-left",
            material=pygfx.TextMaterial(
                alpha_mode="blend",
                aa=True,
                render_queue=RenderQueue.overlay,
                color="w",
                outline_color="w",
                outline_thickness=0.0,
                depth_write=False,
                depth_test=False,
                pick_write=False,
            ),
        )

        # plane for the background of the text object
        geometry = pygfx.plane_geometry(1, 1)
        material = pygfx.MeshBasicMaterial(
            alpha_mode="blend",
            render_queue=RenderQueue.overlay,
            color=(0.1, 0.1, 0.3, 0.95),
            depth_write=False,
            depth_test=False,
        )
        self._plane = pygfx.Mesh(geometry, material)

        # line to outline the plane mesh
        self._line = pygfx.Line(
            geometry=pygfx.Geometry(
                positions=np.array(
                    [
                        [0, 0, 0],
                        [0, 0, 0],
                        [0, 0, 0],
                        [0, 0, 0],
                        [0, 0, 0],
                    ],
                    dtype=np.float32,
                )
            ),
            material=pygfx.LineThinMaterial(
                alpha_mode="blend",
                render_queue=RenderQueue.overlay,
                thickness=1.0,
                color=(0.8, 0.8, 1.0, 1.0),
                depth_write=False,
                depth_test=False,
            ),
        )
        # Plane gets rendered before text and line
        self._plane.render_order = -1

        self._fpl_world_object = pygfx.Group()
        self._fpl_world_object.add(self._plane, self._text, self._line)

        # padded to bbox so the background box behind the text extends a bit further
        # making the text easier to read
        self._padding = np.array([[5, 5, 0], [-5, -5, 0]], dtype=np.float32)

        # position of the tooltip in screen space
        self._position = np.array([0.0, 0.0])

    @property
    def position(self) -> np.ndarray:
        """position of the tooltip in screen space"""
        return self._position

    @property
    def font_size(self):
        """Get or set font size"""
        return self._text.font_size

    @font_size.setter
    def font_size(self, size: float):
        self._text.font_size = size

    @property
    def text_color(self):
        """Get or set text color using a str or RGB(A) array"""
        return self._text.material.color

    @text_color.setter
    def text_color(self, color: str | tuple | list | np.ndarray):
        self._text.material.color = color

    @property
    def background_color(self):
        """Get or set background color using a str or RGB(A) array"""
        return self._plane.material.color

    @background_color.setter
    def background_color(self, color: str | tuple | list | np.ndarray):
        self._plane.material.color = color

    @property
    def outline_color(self):
        """Get or set outline color using a str or RGB(A) array"""
        return self._line.material.color

    @outline_color.setter
    def outline_color(self, color: str | tuple | list | np.ndarray):
        self._line.material.color = color

    @property
    def padding(self) -> np.ndarray:
        """
        Get or set the background padding in number of pixels.
        The padding defines the number of pixels around the tooltip text that the background is extended by.
        """

        return self.padding[0, :2].copy()

    @padding.setter
    def padding(self, padding_xy: tuple[float, float]):
        self._padding[0, :2] = padding_xy
        self._padding[1, :2] = -np.asarray(padding_xy)

    @property
    def visible(self) -> bool:
        return self._fpl_world_object.visible

    @visible.setter
    def visible(self, visible: bool):
        self._fpl_world_object.visible = visible

    def display(self, position: tuple[float, float], info: str):
        """
        display tooltip at the given position in screen space

        Parameters
        ----------
        position: (x, y)
            position in screen space

        info: str
            tooltip text to display

        """
        # set the text and top left position of the tooltip
        self.visible = True
        self._text.set_text(info)
        self._draw_tooltip(position)
        self._position[:] = position

    def _draw_tooltip(self, pos: tuple[float, float]):
        """
        Set the position of the tooltip

        Parameters
        ----------
        pos: [float, float]
            position in screen space

        """
        if np.array_equal(self.position, pos):
            return

        # need to flip due to inverted y
        x, y = pos[0], pos[1]

        # put the tooltip slightly to the top right of the cursor positoin
        x += 8
        y -= 8

        self._text.world.position = (x, -y, 0)

        bbox = self._text.get_world_bounding_box() - self._padding
        [[x0, y0, _], [x1, y1, _]] = bbox

        self._plane.geometry.positions.data[masks.x0] = x0
        self._plane.geometry.positions.data[masks.x1] = x1
        self._plane.geometry.positions.data[masks.y0] = y0
        self._plane.geometry.positions.data[masks.y1] = y1

        self._plane.geometry.positions.update_range()

        # line points
        pts = [[x0, y0], [x0, y1], [x1, y1], [x1, y0], [x0, y0]]

        self._line.geometry.positions.data[:, :2] = pts
        self._line.geometry.positions.update_range()

    def clear(self, *args):
        self._text.set_text("")
        self._fpl_world_object.visible = False


class Tooltip(TextBox):
    def __init__(self):
        super().__init__()
        self._enabled: bool = True
        self._continuous_update = False
        self.visible = False

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = bool(value)

        if not self.enabled:
            self.visible = False

    @property
    def continuous_update(self) -> bool:
        """update the tooltip on every render"""
        return self._continuous_update

    @continuous_update.setter
    def continuous_update(self, value: bool):
        self._continuous_update = bool(value)
