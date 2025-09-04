from functools import partial

import numpy as np
import pygfx

from ..graphics import LineGraphic, ImageGraphic, ScatterGraphic, Graphic
from ..graphics.features import GraphicFeatureEvent


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


class Tooltip:
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
                render_queue=4001,  # overlay
                color="w",
                outline_color="w",
                outline_thickness=0.0,
                pick_write=False,
            ),
        )

        # plane for the background of the text object
        geometry = pygfx.plane_geometry(1, 1)
        material = pygfx.MeshBasicMaterial(
            alpha_mode="blend",
            render_queue=4000,  # overlay
            color=(0.1, 0.1, 0.3, 0.95),
        )
        self._plane = pygfx.Mesh(geometry, material)
        # else text not visible
        self._plane.world.z = 0.5

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
                render_queue=4000,  # overlay
                thickness=1.0,
                color=(0.8, 0.8, 1.0, 1.0),
            ),
        )

        self._world_object = pygfx.Group()
        self._world_object.add(self._plane, self._text, self._line)

        # padded to bbox so the background box behind the text extends a bit further
        # making the text easier to read
        self._padding = np.array([[5, 5, 0], [-5, -5, 0]], dtype=np.float32)

        self._registered_graphics = dict()

    @property
    def world_object(self) -> pygfx.Group:
        return self._world_object

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

    def _set_position(self, pos: tuple[float, float]):
        """
        Set the position of the tooltip

        Parameters
        ----------
        pos: [float, float]
            position in screen space

        """
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

    def _event_handler(self, custom_tooltip: callable, ev: pygfx.PointerEvent):
        """Handles the tooltip appear event, determines the text to be set in the tooltip"""
        if custom_tooltip is not None:
            info = custom_tooltip(ev)

        elif isinstance(ev.graphic, ImageGraphic):
            col, row = ev.pick_info["index"]
            if ev.graphic.data.value.ndim == 2:
                info = str(ev.graphic.data[row, col])
            else:
                info = "\n".join(
                    f"{channel}: {val}"
                    for channel, val in zip("rgba", ev.graphic.data[row, col])
                )

        elif isinstance(ev.graphic, (LineGraphic, ScatterGraphic)):
            index = ev.pick_info["vertex_index"]
            info = "\n".join(
                f"{dim}: {val}" for dim, val in zip("xyz", ev.graphic.data[index])
            )
        else:
            raise TypeError("Unsupported graphic")

        # make the tooltip object visible
        self.world_object.visible = True

        # set the text and top left position of the tooltip
        self._text.set_text(info)
        self._set_position((ev.x, ev.y))

    def _clear(self, ev):
        self._text.set_text("")
        self.world_object.visible = False

    def register(
        self,
        graphic: Graphic,
        appear_event: str = "pointer_move",
        disappear_event: str = "pointer_leave",
        custom_info: callable = None,
    ):
        """
        Register a Graphic to display tooltips.

        **Note:** if the passed graphic is already registered then it first unregistered
        and then re-registered using the given arguments.

        Parameters
        ----------
        graphic: Graphic
            Graphic to register

        appear_event: str, default "pointer_move"
            the pointer that triggers the tooltip to appear. Usually one of "pointer_move" | "click" | "double_click"

        disappear_event: str, default "pointer_leave"
            the event that triggers the tooltip to disappear, does not have to be a pointer event.

        custom_info: callable, default None
            a custom function that takes the pointer event defined as the `appear_event` and returns the text
            to display in the tooltip

        """
        if graphic in list(self._registered_graphics.keys()):
            # unregister first and then re-register
            self.unregister(graphic)

        pfunc = partial(self._event_handler, custom_info)
        graphic.add_event_handler(pfunc, appear_event)
        graphic.add_event_handler(self._clear, disappear_event)

        self._registered_graphics[graphic] = (pfunc, appear_event, disappear_event)

        # automatically unregister when graphic is deleted
        graphic.add_event_handler(self.unregister, "deleted")

    def unregister(self, graphic: Graphic):
        """
        Unregister a Graphic to no longer display tooltips for this graphic.

        **Note:** if the passed graphic is not registered then it is just ignored without raising any exception.

        Parameters
        ----------
        graphic: Graphic
            Graphic to unregister

        """

        if isinstance(graphic, GraphicFeatureEvent):
            # this happens when the deleted event is triggered
            graphic = graphic.graphic

        if graphic not in self._registered_graphics:
            return

        # get pfunc and event names
        pfunc, appear_event, disappear_event = self._registered_graphics.pop(graphic)

        # remove handlers from graphic
        graphic.remove_event_handler(pfunc, appear_event)
        graphic.remove_event_handler(self._clear, disappear_event)

    def unregister_all(self):
        """unregister all graphics"""
        for graphic in self._registered_graphics.keys():
            self.unregister(graphic)
