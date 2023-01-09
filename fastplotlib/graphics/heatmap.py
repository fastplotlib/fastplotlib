import numpy as np
import pygfx
from typing import *
from .image import ImageGraphic

from ..utils import quick_min_max, get_cmap_texture


default_selection_options = {
    "mode": "single",
    "orientation": "row",
    "callbacks": None,
}


class SelectionOptions:
    def __init__(
            self,
            event: str = "double_click",  # click or double_click
            event_button: Union[int, str] = 1,
            mode: str = "single",
            axis: str = "row",
            color: Tuple[int, int, int, int] = None,
            callbacks: List[callable] = None,
    ):
        self.event = event
        self.event_button = event_button
        self.mode = mode
        self.axis = axis

        if color is not None:
            self.color = color

        else:
            self.color = (1, 1, 1, 0.4)

        if callbacks is None:
            self.callbacks = list()
        else:
            self.callbacks = callbacks


class HeatmapGraphic(ImageGraphic):
    def __init__(
            self,
            data: np.ndarray,
            vmin: int = None,
            vmax: int = None,
            cmap: str = 'plasma',
            selection_options: dict = None,
            *args,
            **kwargs
    ):
        """
        Create a Heatmap Graphic

        Parameters
        ----------
        data: array-like, must be 2-dimensional
            | array-like, usually numpy.ndarray, must support ``memoryview()``
            | Tensorflow Tensors also work I think, but not thoroughly tested
        vmin: int, optional
            minimum value for color scaling, calculated from data if not provided
        vmax: int, optional
            maximum value for color scaling, calculated from data if not provided
        cmap: str, optional
            colormap to use to display the image data, default is ``"plasma"``
        selection_options
        args:
            additional arguments passed to Graphic
        kwargs:
            additional keyword arguments passed to Graphic

        """
        super().__init__(data, vmin, vmax, cmap, *args, **kwargs)

        self.selection_options = SelectionOptions()
        self.selection_options.callbacks = list()

        if selection_options is not None:
            for k in selection_options.keys():
                setattr(self.selection_options, k, selection_options[k])

        self.world_object.add_event_handler(
            self.handle_selection_event, self.selection_options.event
        )

        self._highlights = list()

    def handle_selection_event(self, event):
        if not event.button == self.selection_options.event_button:
            return

        if self.selection_options.mode == "single":
            for h in self._highlights:
                self.remove_highlight(h)

        rval = self.add_highlight(event)

        for f in self.selection_options.callbacks:
            f(rval)

    def remove_highlight(self, h):
        self._highlights.remove(h)
        self.world_object.remove(h)

    def add_highlight(self, event):
        index = event.pick_info["index"]

        if self.selection_options.axis == "row":
            index = index[1]
            w = self.data.shape[1]
            h = 1

            pos = ((self.data.shape[1] / 2) - 0.5, index, 1)
            rval = self.data[index, :]  # returned to selection.callbacks functions

        elif self.selection_options.axis == "column":
            index = index[0]
            w = 1
            h = self.data.shape[0]

            pos = (index, (self.data.shape[0] / 2) - 0.5, 1)
            rval = self.data[:, index]

        geometry = pygfx.plane_geometry(
            width=w,
            height=h
        )

        material = pygfx.MeshBasicMaterial(color=self.selection_options.color)

        self.selection_graphic = pygfx.Mesh(geometry, material)
        self.selection_graphic.position.set(*pos)

        self.world_object.add(self.selection_graphic)
        self._highlights.append(self.selection_graphic)

        return rval