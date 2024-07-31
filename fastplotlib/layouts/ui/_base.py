import numpy as np

from imgui_bundle import imgui

from .._plot_area import PlotArea
from .._figure import Figure


class BaseGUI:
    """
    Base class for all ImGUI based GUIs, windows and popups

    The main purpose of this base is for setting a unique ID between multiple figs with identical UI elements

    This ID can be pushed in subclasses within the `update()` method
    """
    ID_COUNTER: int = 0

    def __init__(self):
        BaseGUI.ID_COUNTER += 1
        self._id_counter = BaseGUI.ID_COUNTER

    def update(self):
        """must be implemented in subclass"""
        raise NotImplementedError


class Window(BaseGUI):
    pass


class EdgeWindow(Window):
    def __init__(self, figure: Figure, size: int, fa_icons: imgui.ImFont, *args, **kwargs):
        super().__init__()

        self._figure = figure
        self._size = size
        self._fa_icons = fa_icons

    @property
    def size(self) -> int | None:
        """width or height of the edge window"""
        return self._size

    @size.setter
    def size(self, value):
        if not isinstance(value, int):
            raise TypeError
        self._size = value


class Popup(BaseGUI):
    def __init__(self, figure: Figure, fa_icons: imgui.ImFont, *args, **kwargs):
        super().__init__()

        self._figure = figure
        self._fa_icons = fa_icons

        self._event_filter_names = set()

    def set_event_filter(self, name: str):
        x1, y1 = imgui.get_window_pos()
        width, height = imgui.get_window_size()
        x2, y2 = x1 + width, y1 + height

        if name not in self._figure.renderer.event_filters.keys():
            self._figure.renderer.event_filters[name] = np.array([[x1 - 1, y1 - 1], [x2 + 4, y2 + 4]])
        else:
            self._figure.renderer.event_filters[name][:] = [x1 - 1, y1 - 1], [x2 + 4, y2 + 4]

        self._event_filter_names.add(name)

    def clear_event_filters(self):
        for name in self._event_filter_names:
            self._figure.renderer.event_filters[name][:] = [-1, -1], [-1, -1]
