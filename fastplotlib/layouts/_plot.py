from typing import *

import pygfx
from wgpu.gui.auto import WgpuCanvas

from ._subplot import Subplot
from ._frame import Frame
from ._record_mixin import RecordMixin


class Plot(Subplot, Frame, RecordMixin):
    def __init__(
        self,
        canvas: WgpuCanvas = None,
        renderer: pygfx.WgpuRenderer = None,
        camera: str = "2d",
        controller: Union[pygfx.PanZoomController, pygfx.OrbitController] = None,
        size: Tuple[int, int] = (500, 300),
        **kwargs,
    ):
        """
        Simple Plot object.

        Parameters
        ----------
        canvas: WgpuCanvas, optional
            Canvas for drawing

        renderer: pygfx.Renderer, optional
            pygfx renderer instance

        camera:str, optional
            | One of ``"2d"`` or ``"3d"`` indicating 2D or 3D camera

        controller: None, PanZoomController or OrbitOrthoController, optional
            Usually ``None``, you can pass an existing controller from another
            ``Plot`` or ``Subplot`` within a ``GridPlot`` to synchronize them.

        size: (int, int)
            starting size of canvas, default (500, 300)

        kwargs
            passed to Subplot, for example ``name``

        """
        super(Plot, self).__init__(
            parent=None,
            position=(0, 0),
            parent_dims=(1, 1),
            canvas=canvas,
            renderer=renderer,
            camera=camera,
            controller=controller,
            **kwargs,
        )
        RecordMixin.__init__(self)
        Frame.__init__(self)

        self._starting_size = size

    def render(self):
        """performs a single render of the plot, not for the user"""
        super(Plot, self).render()

        self.renderer.flush()
        self.canvas.request_draw()
