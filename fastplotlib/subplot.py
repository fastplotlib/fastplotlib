import pygfx
from pygfx import Scene, OrthographicCamera, PerspectiveCamera, PanZoomController, Viewport, AxesHelper, GridHelper
from pygfx.linalg import Vector3
from .graphics import *
from .defaults import camera_types, controller_types
from typing import *
from wgpu.gui.auto import WgpuCanvas


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

        self._axes.set_colors('r', 'g', 'b')

        self._grid: GridHelper = GridHelper(size=100, thickness=1)

        self._animate_funcs = list()

    def _produce_rect(self, i, j, w, h):
        # print(locals())
        return [
            ((w / self.ncols) + ((j - 1) * (w / self.ncols))),
            ((h / self.nrows) + ((i - 1) * (h / self.nrows))),
            (w / self.ncols),
            (h / self.nrows)
        ]

    def _resize(self, canvas_dims: Tuple[int, int]):
        # w, h = self.canvas.get_logical_size()
        self.viewport.rect = self._produce_rect(*self.position, *canvas_dims)

    def animate(self, canvas_dims: Tuple[int, int] = None):
        if canvas_dims is None:
            canvas_dims = self.canvas.get_logical_size()

        self.controller.update_camera(self.camera)
        self._resize(canvas_dims)
        self.viewport.render(self.scene, self.camera)

        for f in self._animate_funcs:
            f()

    def add_animations(self, funcs: List[callable]):
        self._animate_funcs += funcs

    def add_graphic(self, graphic):
        self.scene.add(graphic.world_object)

        if isinstance(graphic, Image):
            dims = graphic.data.shape
            zero_pos = Vector3(dims[0] / 2, dims[1] / 2, self.camera.position.z)
            delta = zero_pos.clone().sub(self.camera.position)
            zoom_level = 1 / np.mean(dims)
            if self.controller.zoom_value != zoom_level:
                self.controller.zoom(zoom_level)
            self.controller.pan(delta)

        elif isinstance(graphic, Scatter):
            self.camera.show_object(graphic.world_object)
            # centroid = np.mean(graphic.data, axis=0).tolist()
            # zero_pos = Vector3(*centroid)
            # delta = zero_pos.clone().sub(self.camera.position)
            # zoom_level = 1 / np.mean(graphic.data)
            # if self.controller.zoom_value != zoom_level:
            #     self.controller.zoom(zoom_level)
            # self.controller.pan(delta)

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