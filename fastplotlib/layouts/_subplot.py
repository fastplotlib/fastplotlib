import pygfx
from pygfx import Scene, OrthographicCamera, PerspectiveCamera, PanZoomController, Viewport, AxesHelper, GridHelper
from ..graphics import HeatmapGraphic
from ._defaults import create_camera, create_controller
from typing import *
from wgpu.gui.auto import WgpuCanvas
from warnings import warn
import numpy as np
from math import copysign


class Subplot:
    def __init__(
            self,
            position: Tuple[int, int] = None,
            parent_dims: Tuple[int, int] = None,
            camera: str = '2d',
            controller: Union[pygfx.PanZoomController, pygfx.OrbitOrthoController] = None,
            canvas: WgpuCanvas = None,
            renderer: pygfx.Renderer = None,
            **kwargs
    ):
        self.scene: pygfx.Scene = pygfx.Scene()

        self._graphics = list()

        if canvas is None:
            canvas = WgpuCanvas()

        if renderer is None:
            renderer = pygfx.renderers.WgpuRenderer(canvas)

        self.canvas = canvas
        self.renderer = renderer

        if "name" in kwargs.keys():
            self.name = kwargs["name"]
        else:
            self.name = None

        if position is None:
            position = (0, 0)
        self.position: Tuple[int, int] = position

        if parent_dims is None:
            parent_dims = (1, 1)

        self.nrows, self.ncols = parent_dims

        self.camera: Union[pygfx.OrthographicCamera, pygfx.PerspectiveCamera] = create_camera(camera)

        if controller is None:
            controller = create_controller(camera)
        self.controller: Union[pygfx.PanZoomController, pygfx.OrbitOrthoController] = controller

        # might be better as an attribute of GridPlot
        # but easier to iterate when in same object as camera and scene
        self.viewport: pygfx.Viewport = pygfx.Viewport(renderer)

        self.controller.add_default_event_handlers(
            self.viewport,
            self.camera
        )

        self._axes: AxesHelper = AxesHelper(size=100)
        for arrow in self._axes.children:
            self._axes.remove(arrow)

        self._grid: GridHelper = GridHelper(size=100, thickness=1)

        self._animate_funcs = list()

        self.renderer.add_event_handler(self.set_viewport_rect, "resize")

        self.docked_viewports = dict()
        for pos in ["left", "top", "right", "bottom"]:
            self.docked_viewports[pos] = _DockedViewport(self, pos, size=0)

        self.set_viewport_rect()

    def get_rect(self):
        row_ix, col_ix = self.position
        width_canvas, height_canvas = self.renderer.logical_size

        spacing = 2  # spacing in pixels

        x_pos = ((width_canvas / self.ncols) + ((col_ix - 1) * (width_canvas / self.ncols))) + spacing
        y_pos = ((height_canvas / self.nrows) + ((row_ix - 1) * (height_canvas / self.nrows))) + spacing
        width_subplot = (width_canvas / self.ncols) - spacing
        height_suplot = (height_canvas / self.nrows) - spacing

        return np.array([
            x_pos,
            y_pos,
            width_subplot,
            height_suplot
        ])

    def set_viewport_rect(self, *args):
        rect = self.get_rect()

        for dv in self.docked_viewports.values():
            rect = rect + dv.get_parent_rect_adjust()

        self.viewport.rect = rect

    def animate(self, canvas_dims: Tuple[int, int] = None):
        self.controller.update_camera(self.camera)
        self.viewport.render(self.scene, self.camera)

        for f in self._animate_funcs:
            f()

        for dv in self.docked_viewports.values():
            dv.render()

    def add_animations(self, *funcs: callable):
        for f in funcs:
            if not callable(f):
                raise TypeError(
                    f"all positional arguments to add_animations() must be callable types, you have passed a: {type(f)}"
                )
            self._animate_funcs += funcs

    def add_graphic(self, graphic, center: bool = True):
        if graphic.name is not None:  # skip for those that have no name
            graphic_names = list()

            for g in self._graphics:
                graphic_names.append(g.name)

            if graphic.name in graphic_names:
                raise ValueError(f"graphics must have unique names, current graphic names are:\n {graphic_names}")

        self._graphics.append(graphic)
        self.scene.add(graphic.world_object)

        if isinstance(graphic, HeatmapGraphic):
            self.controller.scale.y = copysign(self.controller.scale.y, -1)

        if center:
            self.center_graphic(graphic)

    def _refresh_camera(self):
        self.controller.update_camera(self.camera)
        if sum(self.renderer.logical_size) > 0:
            scene_lsize = self.viewport.rect[2], self.viewport.rect[3]
        else:
            scene_lsize = (1, 1)

        self.camera.set_view_size(*scene_lsize)
        self.camera.update_projection_matrix()

    def center_graphic(self, graphic, zoom: float = 1.3):
        if not isinstance(self.camera, pygfx.OrthographicCamera):
            warn("`center_graphic()` not yet implemented for `PerspectiveCamera`")
            return

        self._refresh_camera()

        self.controller.show_object(self.camera, graphic.world_object)

        self.controller.zoom(zoom)

    def center_scene(self, zoom: float = 1.3):
        if not len(self.scene.children) > 0:
            return

        if not isinstance(self.camera, pygfx.OrthographicCamera):
            warn("`center_scene()` not yet implemented for `PerspectiveCamera`")
            return

        self._refresh_camera()

        self.controller.show_object(self.camera, self.scene)

        self.controller.zoom(zoom)

    def set_axes_visibility(self, visible: bool):
        if visible:
            self.scene.add(self._axes)
        else:
            self.scene.remove(self._axes)

    def set_grid_visibility(self, visible: bool):
        if visible:
            self.scene.add(self._grid)
        else:
            self.scene.remove(self._grid)

    def get_graphics(self):
        return self._graphics

    def remove_graphic(self, graphic):
        self.scene.remove(graphic.world_object)

    def __getitem__(self, name: str):
        for graphic in self._graphics:
            if graphic.name == name:
                return graphic

        graphic_names = list()
        for g in self._graphics:
            graphic_names.append(g.name)
        raise IndexError(f"no graphic of given name, the current graphics are:\n {graphic_names}")

    def __repr__(self):
        newline = "\n  "
        if self.name is not None:
            return f"'{self.name}' fastplotlib.{self.__class__.__name__} @ {hex(id(self))}\n" \
                   f"Graphics: \n  " \
                   f"{newline.join(graphic.__repr__() for graphic in self.get_graphics())}"
        else:
            return f"fastplotlib.{self.__class__.__name__} @ {hex(id(self))} \n" \
                   f"Graphics: \n  " \
                   f"{newline.join(graphic.__repr__() for graphic in self.get_graphics())}"


class _DockedViewport:
    _valid_positions = [
        "right",
        "left",
        "top",
        "bottom"
    ]

    def __init__(
            self,
            parent: Subplot,
            position: str,
            size: int,
            camera: str = "2d",
    ):
        if position not in self._valid_positions:
            raise ValueError(f"the `position` of an AnchoredViewport must be one of: {self._valid_positions}")

        self.parent = parent
        self.position = position
        self._size = size

        self.viewport = pygfx.Viewport(self.parent.renderer)

        self.scene = pygfx.Scene()
        self.scene.add(
            pygfx.Background(None, pygfx.BackgroundMaterial((0.2, 0.0, 0, 1), (0, 0.0, 0.2, 1)))
        )

        self.camera = pygfx.OrthographicCamera()
        self.controller = pygfx.PanZoomController()

        self.controller.add_default_event_handlers(
            self.viewport,
            self.camera
        )

        self.parent.renderer.add_event_handler(self.set_viewport_rect, "resize")
        self.set_viewport_rect()

    @property
    def size(self) -> int:
        return self._size

    @size.setter
    def size(self, s: int):
        self._size = s
        self.parent.set_viewport_rect()
        self.set_viewport_rect()

    def _get_rect(self, *args):
        if self.size == 0:
            self.viewport.rect = None
            return

        row_ix_parent, col_ix_parent = self.parent.position
        width_canvas, height_canvas = self.parent.renderer.logical_size

        spacing = 2  # spacing in pixels

        if self.position == "right":
                x_pos = (width_canvas / self.parent.ncols) + ((col_ix_parent - 1) * (width_canvas / self.parent.ncols)) + (width_canvas / self.parent.ncols) - self.size
                y_pos = ((height_canvas / self.parent.nrows) + ((row_ix_parent - 1) * (height_canvas / self.parent.nrows))) + spacing
                width_viewport = self.size
                height_viewport = (height_canvas / self.parent.nrows) - spacing

        elif self.position == "left":
                x_pos = (width_canvas / self.parent.ncols) + ((col_ix_parent - 1) * (width_canvas / self.parent.ncols))
                y_pos = ((height_canvas / self.parent.nrows) + ((row_ix_parent - 1) * (height_canvas / self.parent.nrows))) + spacing
                width_viewport = self.size
                height_viewport = (height_canvas / self.parent.nrows) - spacing

        elif self.position == "top":
                x_pos = (width_canvas / self.parent.ncols) + ((col_ix_parent - 1) * (width_canvas / self.parent.ncols)) + spacing
                y_pos = ((height_canvas / self.parent.nrows) + ((row_ix_parent - 1) * (height_canvas / self.parent.nrows))) + spacing
                width_viewport = (width_canvas / self.parent.ncols) - spacing
                height_viewport = self.size

        elif self.position == "bottom":
                x_pos = (width_canvas / self.parent.ncols) + ((col_ix_parent - 1) * (width_canvas / self.parent.ncols)) + spacing
                y_pos = ((height_canvas / self.parent.nrows) + ((row_ix_parent - 1) * (height_canvas / self.parent.nrows))) + (height_canvas / self.parent.nrows) - self.size
                width_viewport = (width_canvas / self.parent.ncols) - spacing
                height_viewport = self.size
        else:
            raise ValueError("invalid position")

        return [x_pos, y_pos, width_viewport, height_viewport]

    def set_viewport_rect(self, *args):
        rect = self._get_rect()

        self.viewport.rect = rect

    def get_parent_rect_adjust(self):
        if self.position == "right":
            return np.array([
                0,  # parent subplot x-position is same
                0,
                -self.size,  # width of parent subplot is `self.size` smaller
                0
            ])

        elif self.position == "left":
            return np.array([
                self.size,  # `self.size` added to parent subplot x-position
                0,
                -self.size,  # width of parent subplot is `self.size` smaller
                0
            ])

        elif self.position == "top":
            return np.array([
                0,
                self.size,  # `self.size` added to parent subplot y-position
                0,
                -self.size,  # height of parent subplot is `self.size` smaller
            ])

        elif self.position == "bottom":
            return np.array([
                0,
                0,  # parent subplot y-position is same,
                0,
                -self.size,  # height of parent subplot is `self.size` smaller
            ])

    def render(self):
        if self.size == 0:
            return

        self.controller.update_camera(self.camera)
        self.viewport.render(self.scene, self.camera)

    def add_graphic(self, graphic, center: bool = True):
        self.scene.add(graphic.world_object)

        if center:
            self.center_graphic(graphic)

    def _refresh_camera(self):
        self.controller.update_camera(self.camera)
        # if sum(self.renderer.logical_size) > 0:
        #     scene_lsize = self.viewport.rect[2], self.viewport.rect[3]
        # else:
        #     scene_lsize = (1, 1)
        #
        # self.camera.set_view_size(*scene_lsize)
        self.camera.update_projection_matrix()

    def center_graphic(self, graphic, zoom: float = 1.3):
        if not isinstance(self.camera, pygfx.OrthographicCamera):
            warn("`center_graphic()` not yet implemented for `PerspectiveCamera`")
            return

        self._refresh_camera()

        self.controller.show_object(self.camera, graphic.world_object)

        self.controller.zoom(zoom)
