import pygfx
from pygfx.linalg import Vector3
from wgpu.gui.auto import WgpuCanvas
from .subplot import Subplot
from .graphics import *


class Plot(Subplot):
    def __init__(
            self,
            canvas: WgpuCanvas = None,
            renderer: pygfx.Renderer = None,
            camera: str = '2d',
            controller: Union[pygfx.PanZoomController, pygfx.OrbitOrthoController] = None
    ):
        super(Plot, self).__init__(
            position=(0, 0),
            parent_dims=(1, 1),
            canvas=canvas,
            renderer=renderer,
            camera=camera,
            controller=controller
        )

    def image(self, *args, **kwargs):
        graphic = Image(*args, **kwargs)
        self.scene.add(graphic.world_object)

        dims = graphic.data.shape
        zero_pos = Vector3(dims[0] / 2, dims[1] / 2, self.camera.position.z)
        delta = zero_pos.clone().sub(self.camera.position)
        zoom_level = 1 / np.mean(dims)
        if self.controller.zoom_value != zoom_level:
            self.controller.zoom(zoom_level)
        self.controller.pan(delta)

        return graphic

    def line(self, *args, **kwargs):
        graphic = Line(*args, **kwargs)
        self.scene.add(graphic.world_object)

        return graphic

    def scatter(self, *args, **kwargs):
        graphic = Scatter(*args, **kwargs)
        self.scene.add(graphic.world_object)
        self.camera.show_object(graphic.world_object)

        return graphic

    def animate(self):
        super(Plot, self).animate(canvas_dims=None)

        self.renderer.flush()
        self.canvas.request_draw()

    def show(self):
        self.canvas.request_draw(self.animate)
        return self.canvas
