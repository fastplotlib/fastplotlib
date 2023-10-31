import os

from ._toolbar import ToolBar

from ...graphics import ImageGraphic

from .._utils import CANVAS_OPTIONS_AVAILABLE


class UnavailableOutputContext:
    # called when a requested output context is not available
    # ex: if trying to force jupyter_rfb canvas but jupyter_rfb is not installed
    def __init__(self, context_name, msg):
        self.context_name = context_name
        self.msg = msg

    def __call__(self, *args, **kwargs):
        raise ModuleNotFoundError(
            f"The following output context is not available: {self.context_name}\n{self.msg}"
        )


# TODO: potentially put all output context and toolbars in their own module and have this determination done at import
if CANVAS_OPTIONS_AVAILABLE["jupyter"]:
    from ._jupyter_output import JupyterOutputContext
else:
    JupyterOutputContext = UnavailableOutputContext(
        "Jupyter",
        "You must install fastplotlib using the `'notebook'` option to use this context:\n"
        'pip install "fastplotlib[notebook]"'
    )

if CANVAS_OPTIONS_AVAILABLE["qt"]:
    from ._qt_output import QOutputContext
else:
    QtOutput = UnavailableOutputContext(
        "Qt",
        "You must install `PyQt6` to use this output context"
    )


class Frame:
    """
    Mixin class for Plot and GridPlot that "frames" the plot.

    Gives them their `show()` call that returns the appropriate output context.
    """
    def __init__(self):
        self._output = None

    @property
    def toolbar(self) -> ToolBar:
        """ipywidget or QToolbar instance"""
        return self._output.toolbar

    @property
    def widget(self):
        """ipywidget or QWidget that contains this plot"""
        # @caitlin: this is the same as the output context, but I figure widget is a simpler public name
        return self._output

    def render(self):
        """render call implemented in subclass"""
        raise NotImplemented

    def _autoscale_init(self, maintain_aspect: bool):
        """autoscale function that is called only during show()"""
        if hasattr(self, "_subplots"):
            for subplot in self:
                if maintain_aspect is None:
                    _maintain_aspect = subplot.camera.maintain_aspect
                else:
                    _maintain_aspect = maintain_aspect
                subplot.auto_scale(maintain_aspect=_maintain_aspect, zoom=0.95)
        else:
            if maintain_aspect is None:
                maintain_aspect = self.camera.maintain_aspect
            self.auto_scale(maintain_aspect=maintain_aspect, zoom=0.95)

    def start_render(self):
        """start render cycle"""
        self.canvas.request_draw(self.render)
        self.canvas.set_logical_size(*self._starting_size)

    def show(
            self,
            autoscale: bool = True,
            maintain_aspect: bool = None,
            toolbar: bool = True,
            sidecar: bool = False,
            sidecar_kwargs: dict = None,
            add_widgets: list = None,
    ):
        """
        Begins the rendering event loop and shows the plot in the desired output context (jupyter, qt or glfw).

        Parameters
        ----------
        autoscale: bool, default ``True``
            autoscale the Scene

        maintain_aspect: bool, default ``True``
            maintain aspect ratio

        toolbar: bool, default ``True``
            show toolbar

        sidecar: bool, default ``True``
            display plot in a ``jupyterlab-sidecar``, only for jupyter output context

        sidecar_kwargs: dict, default ``None``
            kwargs for sidecar instance to display plot
            i.e. title, layout

        add_widgets: list of widgets
            a list of ipywidgets or QWidget that are vertically stacked below the plot

        Returns
        -------
        OutputContext
            In jupyter, it will display the plot in the output cell or sidecar

            In Qt, it will display the Plot, toolbar, etc. as stacked widget, use `Plot.widget` to access it.
        """

        # show was already called, return existing output context
        if self._output is not None:
            return self._output

        self.start_render()

        if sidecar_kwargs is None:
            sidecar_kwargs = dict()

        if add_widgets is None:
            add_widgets = list()

        # flip y axis if ImageGraphics are present
        if hasattr(self, "_subplots"):
            for subplot in self:
                for g in subplot.graphics:
                    if isinstance(g, ImageGraphic):
                        subplot.camera.local.scale_y *= -1
                        break
        else:
            for g in self.graphics:
                if isinstance(g, ImageGraphic):
                    self.camera.local.scale_y *= -1
                    break

        if autoscale:
            self._autoscale_init(maintain_aspect)

        # used for generating images in docs using nbsphinx
        if "NB_SNAPSHOT" in os.environ.keys():
            if os.environ["NB_SNAPSHOT"] == "1":
                return self.canvas.snapshot()

        # return the appropriate OutputContext based on the current canvas
        if self.canvas.__class__.__name__ == "JupyterWgpuCanvas":
            self._output = JupyterOutputContext(
                frame=self,
                make_toolbar=toolbar,
                use_sidecar=sidecar,
                sidecar_kwargs=sidecar_kwargs,
                add_widgets=add_widgets,
            )

        elif self.canvas.__class__.__name__ == "QWgpuCanvas":
            self._output = QOutputContext(
                frame=self,
                make_toolbar=toolbar,
                add_widgets=add_widgets
            )

        else:  # assume GLFW, the output context is just the canvas
            self._output = self.canvas

        # return the output context, this call is required for jupyter but not for Qt
        return self._output

    def close(self):
        """Close the output context"""
        self._output.close()
