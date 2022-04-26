from pygfx import Scene, OrthographicCamera, PerspectiveCamera, PanZoomController, Viewport
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
