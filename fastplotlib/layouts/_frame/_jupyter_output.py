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

        if not make_toolbar and not use_sidecar:
            self.output = frame.canvas

        if make_toolbar:
            self.toolbar = IpywidgetToolBar(frame)
            self.output = VBox([frame.canvas, frame.toolbar])

        if use_sidecar:
            self.sidecar = Sidecar(**sidecar_kwargs)

    def __repr__(self):
        if self.use_sidecar:
            with self.sidecar:
                return display(self.output)
        else:
            return self.output

    def close(self):
        self.frame.canvas.close()

        if self.toolbar is not None:
            self.toolbar.close()

        if self.sidecar is not None:
            self.sidecar.close()
