from typing import *
from ipywidgets import HBox, Checkbox, Layout, Button, ToggleButton, VBox
import pygfx
from wgpu.gui.auto import WgpuCanvas
from .layouts._subplot import Subplot


class Plot(Subplot):
    def __init__(
            self,
            canvas: WgpuCanvas = None,
            renderer: pygfx.Renderer = None,
            camera: str = '2d',
            controller: Union[pygfx.PanZoomController, pygfx.OrbitController] = None,
            toolbar: bool = True,
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

        self.toolbar = toolbar

    def render(self):
        super(Plot, self).render()

        self.renderer.flush()
        self.canvas.request_draw()

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

        if self.toolbar:
            tools = ToolBar(self).toolbar
            return VBox([self.canvas, tools])
        else:
            return self.canvas


class ToolBar:
    def __init__(self,
                 plot: Plot):
        """
        Basic toolbar for a Plot instance.

        Parameters
        ----------
        plot:
        """
        self.plot = plot

        self._tools = list()

        auto_tool = Button(value=False, disabled=False, icon='expand-arrows-alt', layout=Layout(width='auto'))
        center_tool = Button(value=False, disabled=False, icon='compress-arrows-alt', layout=Layout(width='auto'))
        panzoom_tool = ToggleButton(value=False, disabled=False, icon='hand-pointer', layout=Layout(width='auto'))
        maintain_aspect_tool = ToggleButton(value=False, disabled=False, description="1:1", layout=Layout(width='auto'))
        maintain_aspect_tool.style.font_weight = "bold"
        self._tools.extend([auto_tool, center_tool, panzoom_tool, maintain_aspect_tool])

        def auto_scale(obj):
            if maintain_aspect_tool.value:
                self.plot.auto_scale(maintain_aspect=True)
            else:
                self.plot.auto_scale()

        def center_scene(obj):
            self.plot.center_scene()

        def panzoom_control(obj):
            if panzoom_tool.value:
                # toggle pan zoom controller
                self.plot.controller.enabled = False
            else:
                self.plot.controller.enabled = True

        panzoom_tool.observe(panzoom_control, 'value')
        auto_tool.on_click(auto_scale)
        center_tool.on_click(center_scene)

    @property
    def toolbar(self):
        return HBox(self._tools)
