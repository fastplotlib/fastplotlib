from functools import partial

import numpy as np
import pygfx
from .. import ScatterGraphic

from ..graphics import LineGraphic, ImageGraphic, TextGraphic


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
        self._text = pygfx.Text(
            text="",
            font_size=12,
            screen_space=False,
            anchor="bottom-left",
            material=pygfx.TextMaterial(
                color="w",
                outline_color="w",
                outline_thickness=0.0,
                pick_write=False,
            ),
        )

        geometry = pygfx.plane_geometry(1, 1)
        material = pygfx.MeshBasicMaterial(color=(0.1, 0.1, 0.3, 1.))
        self._plane = pygfx.Mesh(geometry, material)
        # else text not visible
        self._plane.world.z = 0.5

        # line to outline the mesh
        self._line = pygfx.Line(
            geometry=pygfx.Geometry(
                    positions=np.array([
                        [0, 0, 0],
                        [0, 0, 0],
                        [0, 0, 0],
                        [0, 0, 0],
                        [0, 0, 0],
                    ], dtype=np.float32)
            ),
            material=pygfx.LineThinMaterial(
                thickness=1.0, color=(0.8, 0.8, 1.0, 1.0)
            )
        )


        self._world_object = pygfx.Group()
        self._world_object.add(self._plane, self._text, self._line)

        # padded to bbox so the background box behind the text extends a bit further
        # making the text easier to read
        self._padding = np.array(
            [[5, 5, 0],
             [-5, -5, 0]],
            dtype=np.float32

        )

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

        self._text.world.position = (x, -y, 0)

        bbox = self._text.get_world_bounding_box() - self._padding
        [[x0, y0, _], [x1, y1, _]] = bbox

        self._plane.geometry.positions.data[masks.x0] = x0
        self._plane.geometry.positions.data[masks.x1] = x1
        self._plane.geometry.positions.data[masks.y0] = y0
        self._plane.geometry.positions.data[masks.y1] = y1

        self._plane.geometry.positions.update_range()

        # line points
        pts = [
            [x0, y0],
            [x0, y1],
            [x1, y1],
            [x1, y0],
            [x0, y0]
        ]

        self._line.geometry.positions.data[:, :2] = pts
        self._line.geometry.positions.update_range()

    def _event_handler(self, display_property, ev: pygfx.PointerEvent):
        if isinstance(ev.graphic, ImageGraphic):
            col, row = ev.pick_info["index"]
            info = ev.graphic.data[row, col]
            self._text.set_text(str(info))

        elif isinstance(ev.graphic, (LineGraphic, ScatterGraphic)):
            index = ev.pick_info["vertex_index"]
            info = ev.graphic.data[index]
            self._text.set_text(str(info))

        self._set_position((ev.x, ev.y))

    def _clear(self, ev):
        self._text.set_text("")

        self._text.world.position = (-1, -1, 0)

        self._plane.geometry.positions.data[masks.x0] = -1
        self._plane.geometry.positions.data[masks.x1] = -1
        self._plane.geometry.positions.data[masks.y0] = -1
        self._plane.geometry.positions.data[masks.y1] = -1

        self._plane.geometry.positions.update_range()

        # line points
        self._line.geometry.positions.data[:, :2] = -1
        self._line.geometry.positions.update_range()

    def register_graphic(
        self,
        graphic,
        event_type: str = "pointer_move",
        display_property: str = "data",
        formatter: callable = None,
    ):
        graphic.add_event_handler(partial(self._event_handler, display_property), event_type)
        graphic.add_event_handler(self._clear, "pointer_leave")
