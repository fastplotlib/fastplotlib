import pygfx
from wgpu.gui.auto import WgpuCanvas
from .layouts._subplot import Subplot
from . import graphics
from functools import partial
from inspect import signature
from typing import *


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

        for graphic_cls_name in graphics.__all__:
            cls = getattr(graphics, graphic_cls_name)
            pfunc = partial(self._create_graphic, cls)
            pfunc.__signature__ = signature(cls)
            pfunc.__doc__ = cls.__doc__
            setattr(self, graphic_cls_name.rstrip("Graphic").lower(), pfunc)

    def _create_graphic(self, graphic_class, *args, **kwargs):
        graphic = graphic_class(*args, **kwargs)
        super(Plot, self).add_graphic(graphic, center=False)

        return graphic

    def animate(self):
        super(Plot, self).animate(canvas_dims=None)

        self.renderer.flush()
        self.canvas.request_draw()

    def show(self):
        self.canvas.request_draw(self.animate)
        self.center_scene()

        return self.canvas
