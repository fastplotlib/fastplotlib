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

    def render(self):
        super(Plot, self).render()

        self.renderer.flush()
        self.canvas.request_draw()

    def show(self):
        """
        begins the rendering event loop and returns the canvas

        Returns
        -------
        WgpuCanvas
            the canvas

        """
        self.canvas.request_draw(self.render)
        self.auto_scale(maintain_aspect=True, zoom=0.95)

        return self.canvas
