from typing import *
from ipywidgets import HBox, Layout, Button, ToggleButton, VBox
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

    def show(self, autoscale: bool = True, toolbar: bool = True):
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

        if toolbar:
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
        plot: encapsulated plot instance that will be manipulated using the toolbar buttons
        """
        self.plot = plot

        self.autoscale_button = Button(value=False, disabled=False, icon='expand-arrows-alt',
                                       layout=Layout(width='auto'), tooltip='Auto-scale the camera w.r.t to the scene')
        self.center_scene_button = Button(value=False, disabled=False, icon='compress-arrows-alt',
                                          layout=Layout(width='auto'), tooltip='Auto-center the scene, does not scale')
        self.panzoom_controller_button = ToggleButton(value=True, disabled=False, icon='hand-pointer',
                                                      layout=Layout(width='auto'), tooltip='Toggle panzoom controller')
        self.maintain_aspect_button = ToggleButton(value=True, disabled=False, description="1:1",
                                                   layout=Layout(width='auto'),
                                                   tooltip='Maintain camera aspect ratio for all dims')
        self.maintain_aspect_button.style.font_weight = "bold"

        self._widget = HBox([self.autoscale_button,
                             self.center_scene_button,
                             self.panzoom_controller_button,
                             self.maintain_aspect_button])

        def auto_scale(obj):
            if self.maintain_aspect_button.value:
                self.plot.auto_scale(maintain_aspect=True)
            else:
                self.plot.auto_scale()

        def center_scene(obj):
            self.plot.center_scene()

        def panzoom_control(obj):
            self.plot.controller.enabled = self.panzoom_controller_button.value

        self.panzoom_controller_button.observe(panzoom_control, 'value')
        self.autoscale_button.on_click(auto_scale)
        self.center_scene_button.on_click(center_scene)

    @property
    def toolbar(self):
        return self._widget
