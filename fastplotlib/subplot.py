from pygfx import Scene, OrthographicCamera, PerspectiveCamera, PanZoomController, Viewport, AxesHelper, GridHelper
from pygfx.linalg import Vector3
from .graphics import *
from typing import *


class Subplot:
    def __init__(self):
        self.scene: pygfx.Scene = None
        self.camera: Union[pygfx.OrthographicCamera, pygfx.PerspectiveCamera] = None
        self.controller: pygfx.PanZoomController = None
        self.viewport: pygfx.Viewport  # might be better as an attribute of GridPlot
        # but easier to iterate when in same object as camera and scene
        self.position: Tuple[int, int] = None
        self.get_rect: callable = None

        self._axes: AxesHelper = AxesHelper(size=100)
        self._axes.set_colors('r', 'g', 'b')

        self._grid: GridHelper = GridHelper(size=100, thickness=1)

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