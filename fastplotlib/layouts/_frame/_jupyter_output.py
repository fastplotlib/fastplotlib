from ipywidgets import VBox, Widget
from sidecar import Sidecar
from IPython.display import display

from ._ipywidget_toolbar import IpywidgetToolBar


class JupyterOutputContext(VBox):
    def __init__(
            self,
            frame,
            make_toolbar,
            use_sidecar,
            sidecar_kwargs,
            add_widgets,
    ):
        self.frame = frame
        self.toolbar = None
        self.sidecar = None

        if add_widgets is None:
            add_widgets = list()
        else:
            if False in [isinstance(w, Widget) for w in add_widgets]:
                raise TypeError(
                    f"add_widgets must be list of ipywidgets, you have passed:\n{add_widgets}"
                )

        self.use_sidecar = use_sidecar

        if not make_toolbar:
            self.output = (frame.canvas,)

        if make_toolbar:
            self.toolbar = IpywidgetToolBar(frame)
            self.output = (frame.canvas, self.toolbar, *add_widgets)

        if use_sidecar:
            self.sidecar = Sidecar(**sidecar_kwargs)

        super().__init__(self.output)

    def _repr_mimebundle_(self, *args, **kwargs):
        if self.use_sidecar:
            with self.sidecar:
                # TODO: prints all the children called, will figure out later
                return display(VBox(self.output))
        else:
            return super()._repr_mimebundle_(*args, **kwargs)

    def close(self):
        self.frame.canvas.close()

        if self.toolbar is not None:
            self.toolbar.close()

        if self.sidecar is not None:
            self.sidecar.close()
