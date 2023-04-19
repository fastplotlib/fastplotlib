from typing import *
import pygfx
from wgpu.gui.auto import WgpuCanvas
from .layouts._subplot import Subplot
from .utils.record import VideoWriter
from multiprocessing import Queue
from time import time


class Plot(Subplot):
    def __init__(
            self,
            canvas: WgpuCanvas = None,
            renderer: pygfx.Renderer = None,
            camera: str = '2d',
            controller: Union[pygfx.PanZoomController, pygfx.OrbitController] = None,
            **kwargs
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

        kwargs
            passed to Subplot, for example ``name``

        Examples
        --------

        Simple example

        .. code-block:: python

            from fastplotlib import Plot

            # create a `Plot` instance
            plot1 = Plot()

            # make some random 2D image data
            data = np.random.rand(512, 512)

            # plot the image data
            plot1.add_image(data=data)

            # show the plot
            plot1.show()

        Sharing controllers, start from the previous example and create a new jupyter cell

        .. code-block:: python

            # use the controller from the previous plot
            # this will sync the pan & zoom controller
            plot2 = Plot(controller=plot1.controller)

            # make some random 2D image data
            data = np.random.rand(512, 512)

            # plot the image data
            plot2.add_image(data=data)

            # show the plot
            plot2.show()

        """
        super(Plot, self).__init__(
            position=(0, 0),
            parent_dims=(1, 1),
            canvas=canvas,
            renderer=renderer,
            camera=camera,
            controller=controller,
            **kwargs
        )

        self._record_writer: VideoWriter = None
        self._record_queue = Queue()
        self._record_fps = 30
        self._record_timer = 0

    def render(self):
        super(Plot, self).render()

        self.renderer.flush()
        self.canvas.request_draw()

    def _record(self):
        t = time()
        if t - self._record_timer < (1 / self._record_fps):
            return

        self._record_timer = t

        if self._record_writer is not None:
            ss = self.canvas.snapshot()
            # exclude alpha channel
            self._record_queue.put(ss.data[:, :, :-1])
            # self._record_writer.writer.write(ss.data[:, :, -1])

    def record_start(self, path, fps: int = 30, fourcc: str = "XVID"):
        """start a recording"""
        self._record_queue = Queue()

        ss = self.canvas.snapshot()

        self._record_writer = VideoWriter(
            path=path,
            queue=self._record_queue,
            fps=fps,
            dims=(ss.width, ss.height)
        )
        self._record_writer.start()

        self._record_fps = fps
        self._record_timer = time()

        self.add_animations(self._record)

    def record_stop(self):
        """end a current recording"""
        self._record_queue.put(None)
        self._record_writer = None

        self.remove_animation(self._record)

    def show(self, autoscale: bool = True):
        """
        begins the rendering event loop and returns the canvas

        Returns
        -------
        WgpuCanvas
            the canvas

        """
        self.canvas.request_draw(self.render)
        if autoscale:
            self.auto_scale(maintain_aspect=True, zoom=0.95)

        return self.canvas
