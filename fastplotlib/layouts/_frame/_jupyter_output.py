from typing import *

from ipywidgets import VBox, Widget
from sidecar import Sidecar
from IPython.display import display

from ._ipywidget_toolbar import IpywidgetToolBar


class JupyterOutputContext(VBox):
    """
    Output context to display plots in jupyter. Inherits from ipywidgets.VBox

    Basically vstacks plot canvas, toolbar, and other widgets. Uses sidecar if desired.
    """
    def __init__(
            self,
            frame,
            make_toolbar: bool,
            use_sidecar: bool,
            sidecar_kwargs: dict,
            add_widgets: List[Widget],
    ):
        """

        Parameters
        ----------
        frame:
            Plot frame for which to generate the output context

        sidecar_kwargs: dict
            optional kwargs passed to Sidecar

        add_widgets: List[Widget]
            list of ipywidgets to stack below the plot and toolbar
        """
        self.frame = frame
        self.toolbar = None
        self.sidecar = None

        # verify they are all valid ipywidgets
        if False in [isinstance(w, Widget) for w in add_widgets]:
            raise TypeError(
                f"add_widgets must be list of ipywidgets, you have passed:\n{add_widgets}"
            )

        self.use_sidecar = use_sidecar

        if not make_toolbar:  # just stack canvas and the additional widgets, if any
            self.output = (frame.canvas, *add_widgets)

        if make_toolbar:  # make toolbar and stack canvas, toolbar, add_widgets
            self.toolbar = IpywidgetToolBar(frame)
            self.output = (frame.canvas, self.toolbar, *add_widgets)

        if use_sidecar:  # instantiate sidecar if desired
            self.sidecar = Sidecar(**sidecar_kwargs)

        # stack all of these in the VBox
        super().__init__(self.output)

    def _repr_mimebundle_(self, *args, **kwargs):
        """
        This is what jupyter hook into when this output context instance is returned at the end of a cell.
        """
        if self.use_sidecar:
            with self.sidecar:
                # TODO: prints all the child widgets in the cell output, will figure out later, sidecar output works
                return display(VBox(self.output))
        else:
            # just display VBox contents in cell output
            return super()._repr_mimebundle_(*args, **kwargs)

    def close(self):
        """Closes the output context, cleanup all the stuff"""
        self.frame.canvas.close()

        if self.toolbar is not None:
            self.toolbar.close()

        if self.sidecar is not None:
            self.sidecar.close()

        super().close()  # ipywidget VBox cleanup
