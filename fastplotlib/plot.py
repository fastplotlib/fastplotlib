from typing import *
import pygfx
from wgpu.gui.auto import WgpuCanvas
from .layouts._subplot import Subplot


class Plot(Subplot):
    def __init__(
            self,
            canvas: WgpuCanvas = None,
            renderer: pygfx.Renderer = None,
            camera: str = '2d',
            controller: Union[pygfx.PanZoomController, pygfx.OrbitOrthoController] = None,
            **kwargs
    ):
        super(Plot, self).__init__(
            position=(0, 0),
            parent_dims=(1, 1),
            canvas=canvas,
            renderer=renderer,
            camera=camera,
            controller=controller,
            **kwargs
        )

    def render(self):
        super(Plot, self).render()

        self.renderer.flush()
        self.canvas.request_draw()

    def show(self):
        self.canvas.request_draw(self.render)
        self.center_scene()

        return self.canvas
