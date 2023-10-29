from ipywidgets import VBox
from sidecar import Sidecar
from IPython.display import display

from ._ipywidget_toolbar import IpywidgetToolBar


class JupyterOutput:
    def __init__(
            self,
            frame,
            make_toolbar,
            use_sidecar,
            sidecar_kwargs
    ):
        self.frame = frame
        self.toolbar = None
        self.sidecar = None

        self.use_sidecar = use_sidecar

        if not make_toolbar:
            self.output = frame.canvas

        if make_toolbar:
            self.toolbar = IpywidgetToolBar(frame)
            self.output = VBox([frame.canvas, self.toolbar])

        if use_sidecar:
            self.sidecar = Sidecar(**sidecar_kwargs)

    def _repr_mimebundle_(self, *args, **kwargs):
        if self.use_sidecar:
            with self.sidecar:
                return display(self.output)
        else:
            return self.output._repr_mimebundle_(*args, **kwargs)

    def close(self):
        self.frame.canvas.close()

        if self.toolbar is not None:
            self.toolbar.close()

        if self.sidecar is not None:
            self.sidecar.close()
