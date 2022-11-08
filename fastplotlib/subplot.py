import pygfx
from pygfx import Scene, OrthographicCamera, PerspectiveCamera, PanZoomController, Viewport, AxesHelper, GridHelper
from .defaults import camera_types, controller_types
from .graphics import Heatmap
from typing import *
from wgpu.gui.auto import WgpuCanvas
from warnings import warn
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

        self.camera: Union[pygfx.OrthographicCamera, pygfx.PerspectiveCamera] = camera_types[camera]()

        if controller is None:
            controller = controller_types[camera]()
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

        self.renderer.add_event_handler(self._produce_rect, "resize")

    def _produce_rect(self, *args):#, w, h):
        i, j = self.position

        w, h = self.renderer.logical_size

        spacing = 2  # spacing in pixels

        self.viewport.rect = [
            ((w / self.ncols) + ((j - 1) * (w / self.ncols))) + spacing,
            ((h / self.nrows) + ((i - 1) * (h / self.nrows))) + spacing,
            (w / self.ncols) - spacing,
            (h / self.nrows) - spacing
        ]

    def animate(self, canvas_dims: Tuple[int, int] = None):
        self.controller.update_camera(self.camera)
        self.viewport.render(self.scene, self.camera)

        for f in self._animate_funcs:
            f()

    def add_animations(self, funcs: List[callable]):
        self._animate_funcs += funcs

    def add_graphic(self, graphic, center: bool = True):
        graphic_names = list()

        for g in self._graphics:
            graphic_names.append(g.name)

        if graphic.name in graphic_names:
            raise ValueError(f"graphics must have unique names, current graphic names are:\n {graphic_names}")

        self._graphics.append(graphic)
        self.scene.add(graphic.world_object)

        if isinstance(graphic, Heatmap):
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

    def remove_graphic(self, graphic):
        self.scene.remove(graphic.world_object)

    def get_graphics(self):
        return self._graphics

    def __getitem__(self, name: str):
        for graphic in self._graphics:
            if graphic.name == name:
                return graphic

        graphic_names = list()
        for g in self._graphics:
            graphic_names.append(g.name)
        raise IndexError(f"no graphic of given name, the current graphics are:\n {graphic_names}")
