import numpy as np

from .._subplot import Subplot

class BaseFrame:
    """Mixin class for Plot and GridPlot that gives them the toolbar"""
    def __init__(self, canvas, toolbar):
        """

        Parameters
        ----------
        plot:
            `Plot` or `GridPlot`
        toolbar
        """
        self._canvas = canvas
        self._toolbar = toolbar

        # default points upwards
        self._y_axis: int = 1

        self._plot_type = self.__class__.__name__

    @property
    def selected_subplot(self) -> Subplot:
        if self._plot_type == "GridPlot":
            return self.toolbar.selected_subplot
        else:
            return self

    @property
    def toolbar(self):
        return self._toolbar

    @property
    def panzoom(self) -> bool:
        return self.selected_subplot.controller.enabled

    @property
    def maintain_aspect(self) -> bool:
        return self.selected_subplot.camera.maintain_aspect

    @property
    def y_axis(self) -> int:
        return int(np.sign(self.selected_subplot.camera.local.scale_y))

    @y_axis.setter
    def y_axis(self, value: int):
        """

        Parameters
        ----------
        value: 1 or -1
            1: points upwards, -1: points downwards

        """
        value = int(value)  # in case we had a float 1.0

        if value not in [1, -1]:
            raise ValueError("y_axis value must be 1 or -1")

        sign = np.sign(self.selected_subplot.camera.local.scale_y)

        if sign == value:
            # desired y-axis is already set
            return

        # otherwise flip it
        self.selected_subplot.camera.local.scale_y *= -1

    def render(self):
        raise NotImplemented

    def _autoscale_init(self, maintain_aspect: bool):
        """autoscale function that is called only during show()"""
        if self._plot_type == "GridPlot":
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

    def show(self):
        raise NotImplemented("Must be implemented in subclass")
