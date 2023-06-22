from typing import *
from datetime import datetime
import traceback

import pygfx
from wgpu.gui.auto import WgpuCanvas, is_jupyter

if is_jupyter():
    from ipywidgets import HBox, Layout, Button, ToggleButton, VBox

from .layouts._subplot import Subplot
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
        RecordMixin.__init__(self)

        self._starting_size = size

        self.toolbar = None

    def render(self):
        super(Plot, self).render()

        self.renderer.flush()
        self.canvas.request_draw()

    def show(
            self,
            autoscale: bool = True,
            maintain_aspect: bool = None,
            toolbar: bool = True
    ):
        """
        Begins the rendering event loop and returns the canvas

        Parameters
        ----------
        autoscale: bool, default ``True``
            autoscale the Scene

        maintain_aspect: bool, default ``None``
            maintain aspect ratio, uses ``camera.maintain_aspect`` if ``None``

        toolbar: bool, default True
            show toolbar

        Returns
        -------
        WgpuCanvas
            the canvas

        """
        self.canvas.request_draw(self.render)
            
        self.canvas.set_logical_size(*self._starting_size)

        if maintain_aspect is None:
            maintain_aspect = self.camera.maintain_aspect

        if autoscale:
            self.auto_scale(maintain_aspect=maintain_aspect, zoom=0.95)

        # check if in jupyter notebook, or if toolbar is False
        if (self.canvas.__class__.__name__ != "JupyterWgpuCanvas") or (not toolbar):
            return self.canvas

        if self.toolbar is None:
            self.toolbar = ToolBar(self)
            self.toolbar.maintain_aspect_button.value = maintain_aspect

        return VBox([self.canvas, self.toolbar.widget])

    def close(self):
        """Close Plot"""
        self.canvas.close()

        if self.toolbar is not None:
            self.toolbar.widget.close()


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
        self.flip_camera_button = Button(value=False, disabled=False, icon='arrows-v',
                                         layout=Layout(width='auto'), tooltip='flip')
        self.record_button = ToggleButton(value=False, disabled=False, icon='video',
                                          layout=Layout(width='auto'), tooltip='record')

        self.widget = HBox([self.autoscale_button,
                            self.center_scene_button,
                            self.panzoom_controller_button,
                            self.maintain_aspect_button,
                            self.flip_camera_button,
                            self.record_button])

        self.panzoom_controller_button.observe(self.panzoom_control, 'value')
        self.autoscale_button.on_click(self.auto_scale)
        self.center_scene_button.on_click(self.center_scene)
        self.maintain_aspect_button.observe(self.maintain_aspect, 'value')
        self.flip_camera_button.on_click(self.flip_camera)
        self.record_button.observe(self.record_plot, 'value')

    def auto_scale(self, obj):
        self.plot.auto_scale(maintain_aspect=self.plot.camera.maintain_aspect)

    def center_scene(self, obj):
        self.plot.center_scene()

    def panzoom_control(self, obj):
        self.plot.controller.enabled = self.panzoom_controller_button.value

    def maintain_aspect(self, obj):
        self.plot.camera.maintain_aspect = self.maintain_aspect_button.value

    def flip_camera(self, obj):
        self.plot.camera.world.scale_y *= -1

    def record_plot(self, obj):
        if self.record_button.value:
            try:
                self.plot.record_start(f"./{datetime.now().isoformat(timespec='seconds').replace(':', '_')}.mp4")
            except Exception:
                traceback.print_exc()
                self.record_button.value = False
        else:
            self.plot.record_stop()
