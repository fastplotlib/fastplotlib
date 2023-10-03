import os


from ._frame_base import BaseFrame
from ._toolbar import ToolBar


class FrameNotebook(BaseFrame):
    def show(
            self,
            autoscale: bool = True,
            maintain_aspect: bool = None,
            toolbar: bool = True,
            sidecar: bool = True,
            sidecar_kwargs: dict = None,
            vbox: list = None
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

        vbox: list, default ``None``
            list of ipywidgets to be displayed with plot

        Returns
        -------
        WgpuCanvas
            the canvas

        """

        self._canvas.request_draw(self.render)

        self._canvas.set_logical_size(*self._starting_size)

        if autoscale:
            self._autoscale_init(maintain_aspect)

        if "NB_SNAPSHOT" in os.environ.keys():
            # used for docs
            if os.environ["NB_SNAPSHOT"] == "1":
                return self.canvas.snapshot()

        # check if in jupyter notebook, or if toolbar is False
        if (self.canvas.__class__.__name__ != "JupyterWgpuCanvas") or (not toolbar):
            return self.canvas

        if self.toolbar is None:
            self.toolbar = ToolBar(self)
            self.toolbar.maintain_aspect_button.value = self[
                0, 0
            ].camera.maintain_aspect

        # validate vbox if not None
        if vbox is not None:
            for widget in vbox:
                if not isinstance(widget, Widget):
                    raise ValueError(f"Items in vbox must be ipywidgets. Item: {widget} is of type: {type(widget)}")
            self.vbox = VBox(vbox)

        if not sidecar:
            if self.vbox is not None:
                return VBox([self.canvas, self.toolbar.widget, self.vbox])
            else:
                return VBox([self.canvas, self.toolbar.widget])

        # used when plot.show() is being called again but sidecar has been closed via "x" button
        # need to force new sidecar instance
        # couldn't figure out how to get access to "close" button in order to add observe method on click
        if self.plot_open:
            self.sidecar = None

        if self.sidecar is None:
            if sidecar_kwargs is not None:
                self.sidecar = Sidecar(**sidecar_kwargs)
                self.plot_open = True
            else:
                self.sidecar = Sidecar()
                self.plot_open = True

        with self.sidecar:
            if self.vbox is not None:
                return display(VBox([self.canvas, self.toolbar.widget, self.vbox]))
            else:
                return display(VBox([self.canvas, self.toolbar.widget]))

