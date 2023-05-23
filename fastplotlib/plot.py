from typing import *
import pygfx
from wgpu.gui.auto import WgpuCanvas

from .layouts._subplot import Subplot
from ipywidgets import HBox, Layout, Button, ToggleButton, VBox
from wgpu.gui.jupyter import JupyterWgpuCanvas
from .layouts._record_mixin import RecordMixin


class Plot(Subplot, RecordMixin):
    def __init__(
            self,
            canvas: WgpuCanvas = None,
            renderer: pygfx.Renderer = None,
            camera: str = '2d',
            controller: Union[pygfx.PanZoomController, pygfx.OrbitController] = None,
            size: Tuple[int, int] = (500, 300),
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

        size: (int, int)
            starting size of canvas, default (500, 300)

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
        super(RecordMixin, self).__init__()

        self._starting_size = size

        self.toolbar = None

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
            
        self.canvas.set_logical_size(*self._starting_size)

        # check if in jupyter notebook or not
        if not isinstance(self.canvas, JupyterWgpuCanvas):
            return self.canvas

        if toolbar and self.toolbar is None:
            self.toolbar = ToolBar(self).widget
            return VBox([self.canvas, self.toolbar])
        elif toolbar and self.toolbar is not None:
            return VBox([self.canvas, self.toolbar])
        else:
            return self.canvas

    def close(self):
        self.canvas.close()

        
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
                                       layout=Layout(width='auto'), tooltip='auto-scale scene')
        self.center_scene_button = Button(value=False, disabled=False, icon='align-center',
                                          layout=Layout(width='auto'), tooltip='auto-center scene')
        self.panzoom_controller_button = ToggleButton(value=True, disabled=False, icon='hand-pointer',
                                                      layout=Layout(width='auto'), tooltip='panzoom controller')
        self.maintain_aspect_button = ToggleButton(value=True, disabled=False, description="1:1",
                                                   layout=Layout(width='auto'),
                                                   tooltip='maintain aspect')
        self.maintain_aspect_button.style.font_weight = "bold"
        self.flip_camera_button = Button(value=False, disabled=False, icon='sync-alt',
                                         layout=Layout(width='auto'), tooltip='flip')

        self.widget = HBox([self.autoscale_button,
                            self.center_scene_button,
                            self.panzoom_controller_button,
                            self.maintain_aspect_button,
                            self.flip_camera_button])

        self.panzoom_controller_button.observe(self.panzoom_control, 'value')
        self.autoscale_button.on_click(self.auto_scale)
        self.center_scene_button.on_click(self.center_scene)
        self.maintain_aspect_button.observe(self.maintain_aspect, 'value')
        self.flip_camera_button.on_click(self.flip_camera)

    def auto_scale(self, obj):
        self.plot.auto_scale(maintain_aspect=self.plot.camera.maintain_aspect)

    def center_scene(self, obj):
        self.plot.center_scene()

    def panzoom_control(self, obj):
        self.plot.controller.enabled = self.panzoom_controller_button.value

    def maintain_aspect(self, obj):
        self.plot.camera.maintain_aspect = self.maintain_aspect_button.value

    def flip_camera(self, obj):
        self.plot.camera.scale.y = -1 * self.plot.camera.scale.y
      