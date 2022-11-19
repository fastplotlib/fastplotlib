import pygfx
from pygfx import Scene, OrthographicCamera, PerspectiveCamera, PanZoomController, Viewport, AxesHelper, GridHelper
from .defaults import camera_types, controller_types
from typing import *
from wgpu.gui.auto import WgpuCanvas
from warnings import warn
import numpy as np


class Subplot:
    def __init__(
            self,
            position: Tuple[int, int] = None,
            parent_dims: Tuple[int, int] = None,
            camera: str = '2d',
            controller: Union[pygfx.PanZoomController, pygfx.OrbitOrthoController] = None,
            canvas: WgpuCanvas = None,
            renderer: pygfx.Renderer = None
    ):
        self.scene: pygfx.Scene = pygfx.Scene()

        if canvas is None:
            canvas = WgpuCanvas()

        if renderer is None:
            renderer = pygfx.renderers.WgpuRenderer(canvas)

        self.canvas = canvas
        self.renderer = renderer

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

        self.sub_viewports: Dict[str, Dict[str, Union[pygfx.Viewport, int]]] = dict()

        self.docked_viewports = dict()
        for pos in ["left", "top", "right", "bottom"]:
            self.docked_viewports[pos] = _AnchoredViewport(self, pos, size=0)

        self.docked_viewports["right"].size = 60

        # self.add_sub_viewport("right", size=60)

        self._produce_rect()

    def add_sub_viewport(self, position: str, size: int):
        # TODO: Generalize to all directions
        valid_positions = ["right"]  # only support right for now
        if position not in valid_positions:
            raise ValueError(f"`position` argument must be one of {valid_positions}")

        if position in self.sub_viewports.keys():
            raise KeyError(f"sub_viewport already exists at position: {position}")

        self.sub_viewports[position] = {"viewport": pygfx.Viewport(self.renderer)}
        self.sub_viewports[position]["size"] = size

        # TODO: add camera and controller to sub_viewports
        # self.sub_viewports[position]['camera']
        # self.sub_viewports[position]['controller']

    def get_rect_vector(self):
        i, j = self.position
        w, h = self.renderer.logical_size

        spacing = 2  # spacing in pixels

        return np.array([
            ((w / self.ncols) + ((j - 1) * (w / self.ncols))) + spacing,
            ((h / self.nrows) + ((i - 1) * (h / self.nrows))) + spacing,
            (w / self.ncols) - spacing,
            (h / self.nrows) - spacing
        ])

    def _produce_rect(self, *args):#, w, h):
        i, j = self.position

        w, h = self.renderer.logical_size

        spacing = 2  # spacing in pixels

        rect = self.get_rect_vector()

        for dv in self.docked_viewports.values():
            rect = rect - dv.get_parent_rect_removal()
            # print(dv.get_parent_rect_removal())

        self.viewport.rect = rect

        # self.viewport.rect = np.array([
        #     ((w / self.ncols) + ((j - 1) * (w / self.ncols))) + spacing,
        #     ((h / self.nrows) + ((i - 1) * (h / self.nrows))) + spacing,
        #     (w / self.ncols) - spacing - self.sub_viewports["right"]["size"],
        #     (h / self.nrows) - spacing
        # ])

        # # # TODO: Generalize to all directions
        # for svp in self.sub_viewports.keys():
        #     self.sub_viewports["right"]["viewport"].rect = [
        #         (w / self.ncols) - self.sub_viewports["right"]["size"],
        #         ((h / self.nrows) + ((i - 1) * (h / self.nrows))) + spacing,
        #         (w / self.ncols) - spacing,
        #         (h / self.nrows) - spacing
        #     ]

    def animate(self, canvas_dims: Tuple[int, int] = None):
        self.controller.update_camera(self.camera)
        self.viewport.render(self.scene, self.camera)

        # self.sub_viewports["right"]["viewport"].render()

        for f in self._animate_funcs:
            f()

        for dv in self.docked_viewports.values():
            dv.render()

    def add_animations(self, funcs: List[callable]):
        self._animate_funcs += funcs

    def add_graphic(self, graphic, center: bool = True):
        self.scene.add(graphic.world_object)

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


class _AnchoredViewport:
    _valid_positions = [
        "right",
        "left",
        "top",
        "bottom"
    ]
    # define the index of the parent.viewport.rect vector
    # where this viewport's size should be subtracted
    # from the parent.viewport.rect
    _remove_from_parent = {
        "left": 0,
        "bottom": 1,
        "right": 2,
        "top": 3
    }

    _add_to_parent = {
        "left": 2,
        "bottom": 3,
        "right": 0,
        "top": 0
    }

    # the vector to encode this viewport's position
    _viewport_rect_pos = {
        "left": 0,
        "bottom": 0,
        "right": 1,
        "top": 0
    }

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

        self._produce_rect()
        self.parent.renderer.add_event_handler(self._produce_rect, "resize")

    @property
    def size(self) -> int:
        return self._size

    @size.setter
    def size(self, s: int):
        self._size = s
        self._produce_rect()

    def _produce_rect(self, *args):
        if self.size == 0:
            self.viewport.rect = None
            return

        i, j = self.parent.position
        w, h = self.parent.renderer.logical_size

        spacing = 2  # spacing in pixels

        parent_rect = self.parent.get_rect_vector()

        v = np.zeros(4)
        v[self._viewport_rect_pos[self.position]] = 1

        # self.viewport.rect = parent_rect - (v * self.size)

        self.viewport.rect = [
            (w / self.parent.ncols) + ((j - 1) * (w / self.parent.ncols)) + (w / self.parent.ncols) - self.size,
            ((h / self.parent.nrows) + ((i - 1) * (h / self.parent.nrows))) + spacing,
            self.size,
            (h / self.parent.nrows) - spacing
        ]

        print(self.viewport.rect)

    def get_parent_rect_removal(self):
        ix = self._remove_from_parent[self.position]
        ix2 = self._add_to_parent[self.position]

        v = np.zeros(4)
        v[ix] = 1

        # v[ix2] = - 1

        return v * self.size

    def render(self):
        if self.size == 0:
            return

        # self._produce_rect()
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
