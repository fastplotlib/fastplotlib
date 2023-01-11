from typing import *

import numpy as np

import pygfx
from pygfx import TransformGizmo, Color
from ipywidgets import IntSlider

from ._base import Graphic


class LineSlider(Graphic):
    def __init__(
            self,
            orientation: str = "v",
            x_pos: float = None,
            y_pos: float = None,
            bounds: Tuple[int, int] = None,
            slider: IntSlider = None,
            thickness: float = 2.5,
            color: Any = "w",
            name: str = None,
    ):
        """
        Create a horizontal or vertical line slider that is synced to an ipywidget IntSlider

        Parameters
        ----------
        orientation: str, default "v"
            one of "v" - vertical, or "h" - horizontal

        x_pos: float, optional
            x-position of slider

        y_pos: float, optional
            y-position of slider

        bounds: 2-element int tuple, optional
            set length of slider by bounding it between two x-pos or two y-pos

        slider: IntSlider, optional
            pygfx slider to handle event for slider

        thickness: float, default 2.5
            thickness of the slider

        color: Any, default "w"
            value to set the color of the slider

        name: str, optional
            name of line slider
        """
        if orientation == "v":
            if x_pos is None:
                raise ValueError("Must pass `x_pos` if orientation is 'v'")

            xs = np.zeros(2)
            ys = np.array([bounds[0], bounds[1]])
            zs = np.zeros(2)

            data = np.ascontiguousarray(np.array([xs, ys, zs]).T).astype(np.float32)

        elif orientation == "h":
            raise ValueError("'h' not yet supported")
            if y_pos is None:
                raise ValueError("Must pass `y_pos` if orientation is 'h'")

        else:
            raise ValueError("`orientation` must be one of 'v' or 'h'")

        if thickness < 1.1:
            material = pygfx.LineThinMaterial
        else:
            material = pygfx.LineMaterial

        colors_inner = np.repeat([Color("w")], 2, axis=0).astype(np.float32)
        colors_outer = np.repeat([Color([1., 1., 1., 0.25])], 2, axis=0).astype(np.float32)

        line_inner = pygfx.Line(
            # self.data.feature_data because data is a Buffer
            geometry=pygfx.Geometry(positions=data, colors=colors_inner),
            material=material(thickness=thickness, vertex_colors=True)
        )

        line_outer = pygfx.Line(
            geometry=pygfx.Geometry(positions=data, colors=colors_outer),
            material=material(thickness=thickness + 4, vertex_colors=True)
        )

        self._world_object = pygfx.Group()

        self._world_object.add(line_outer)
        self._world_object.add(line_inner)

        self.position.x = x_pos

        self.slider = slider
        self.slider.observe(self.set_position, "value")

        self.name = name

    def set_position(self, change):
        self.position.x = change["new"]

    # def _add_plot_area_hook(self, viewport, camera):
    #     self.gizmo = TransformGizmo(self.world_object)
    #     self.gizmo.add_default_event_handlers(viewport, camera)
