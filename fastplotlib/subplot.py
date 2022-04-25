import pygfx
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
            self.camera.set_view_size(*dims)
            self.camera.position.set(dims[0] / 2, dims[1] / 2, 0)
            self.controller.update_camera(self.camera)