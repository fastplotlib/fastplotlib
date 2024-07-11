from ipywidgets import VBox, Widget
from sidecar import Sidecar
from IPython.display import display


class JupyterOutputContext(VBox):
    """
    Output context to display plots in jupyter. Inherits from ipywidgets.VBox

    Basically vstacks plot canvas, toolbar, and other widgets. Uses sidecar if desired.
    """

    def __init__(
        self,
        frame,
        use_sidecar: bool,
        sidecar_kwargs: dict,
    ):
        """

        Parameters
        ----------
        frame:
            Plot frame for which to generate the output context

        sidecar_kwargs: dict
            optional kwargs passed to Sidecar

        """
        self.frame = frame
        self.toolbar = None
        self.sidecar = None

        self.use_sidecar = use_sidecar

        self.output = (frame.canvas,)

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

        if self.sidecar is not None:
            self.sidecar.close()

        super().close()  # ipywidget VBox cleanup
