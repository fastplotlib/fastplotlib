import os

from ._toolbar import ToolBar

from .._utils import CANVAS_OPTIONS_AVAILABLE

class UnavailableOutputContext:
    def __init__(self, *arg, **kwargs):
        raise ModuleNotFoundError("Unavailable output context")


if CANVAS_OPTIONS_AVAILABLE["jupyter"]:
    from ._jupyter_output import JupyterOutput
else:
    JupyterOutput = UnavailableOutputContext

if CANVAS_OPTIONS_AVAILABLE["qt"]:
    from ._qt_output import QtOutput
else:
    JupyterOutput = UnavailableOutputContext


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

    def render(self):
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

    def show(
            self,
            autoscale: bool = True,
            maintain_aspect: bool = None,
            toolbar: bool = True,
            sidecar: bool = False,
            sidecar_kwargs: dict = None,
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
        if self._output is not None:
            return self._output

        self.canvas.request_draw(self.render)
        self.canvas.set_logical_size(*self._starting_size)

        if autoscale:
            self._autoscale_init(maintain_aspect)

        if "NB_SNAPSHOT" in os.environ.keys():
            # used for docs
            if os.environ["NB_SNAPSHOT"] == "1":
                return self.canvas.snapshot()

        if self.canvas.__class__.__name__ == "JupyterWgpuCanvas":
            return JupyterOutput(
                frame=self,
                make_toolbar=toolbar,
                use_sidecar=sidecar,
                sidecar_kwargs=sidecar_kwargs
            )

        elif self.canvas.__class__.__name__ == "QWgpuCanvas":
            QtOutput(
                frame=self,
                make_toolbar=toolbar,
            )

    def close(self):
        self._output.close()
