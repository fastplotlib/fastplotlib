import os

from ._toolbar import ToolBar

from ...graphics import ImageGraphic

from .._utils import CANVAS_OPTIONS_AVAILABLE


class UnavailableOutputContext:
    def __init__(self, context_name, msg):
        self.context_name = context_name
        self.msg = msg

    def __call__(self, *args, **kwargs):
        raise ModuleNotFoundError(
            f"The following output context is not available: {self.context_name}\n{self.msg}"
        )


if CANVAS_OPTIONS_AVAILABLE["jupyter"]:
    from ._jupyter_output import JupyterOutput
else:
    JupyterOutput = UnavailableOutputContext(
        "Jupyter",
        "You must install `jupyter_rfb` to use this output context"
    )

if CANVAS_OPTIONS_AVAILABLE["qt"]:
    from ._qt_output import QtOutput
else:
    QtOutput = UnavailableOutputContext(
        "Qt",
        "You must install `PyQt6` to use this output context"
    )


# Single class for PlotFrame to avoid determining inheritance at runtime
class Frame:
    """Mixin class for Plot and GridPlot that gives them the toolbar"""
    def __init__(self):
        """

        Parameters
        ----------
        plot:
            `Plot` or `GridPlot`
        toolbar
        """
        self._plot_type = self.__class__.__name__
        self._output = None

    @property
    def toolbar(self) -> ToolBar:
        return self._output.toolbar

    def _render_step(self):
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
        Begins the rendering event loop and returns the canvas

        Parameters
        ----------
        autoscale: bool, default ``True``
            autoscale the Scene

        maintain_aspect: bool, default ``True``
            maintain aspect ratio

        toolbar: bool, default ``True``
            show toolbar

        sidecar: bool, default ``True``
            display plot in a ``jupyterlab-sidecar``

        sidecar_kwargs: dict, default ``None``
            kwargs for sidecar instance to display plot
            i.e. title, layout

        Returns
        -------
        WgpuCanvas
            the canvas

        """

        # show was already called, return existing output context
        if self._output is not None:
            return self._output

        self.start_render()

        if sidecar_kwargs is None:
            sidecar_kwargs = dict()

        # flip y axis if ImageGraphics are present
        if hasattr(self, "_subplots"):
            for subplot in self:
                for g in subplot:
                    if isinstance(g, ImageGraphic):
                        subplot.camera.local.scale_y = -1
                        break
        else:
            for g in self.graphics:
                if isinstance(g, ImageGraphic):
                    self.camera.local.scale_y = -1
                    break

        if autoscale:
            self._autoscale_init(maintain_aspect)

        if "NB_SNAPSHOT" in os.environ.keys():
            # used for docs
            if os.environ["NB_SNAPSHOT"] == "1":
                return self.canvas.snapshot()

        if self.canvas.__class__.__name__ == "JupyterWgpuCanvas":
            self._output = JupyterOutput(
                frame=self,
                make_toolbar=toolbar,
                use_sidecar=sidecar,
                sidecar_kwargs=sidecar_kwargs,
                add_widgets=add_widgets,
            )

        elif self.canvas.__class__.__name__ == "QWgpuCanvas":
            QtOutput(
                frame=self,
                make_toolbar=toolbar,
            )

        return self._output

    def close(self):
        self._output.close()
