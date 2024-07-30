from imgui_bundle import imgui

from .._plot_area import PlotArea
from .._figure import Figure


class BaseGUI:
    # used for pushing unique ID between multiple figs with identical UI elements
    ID_COUNTER: int = 0

    def __init__(self, owner: PlotArea | Figure, fa_icons: imgui.ImFont, size: int | None):
        BaseGUI.ID_COUNTER += 1
        self._id_counter = BaseGUI.ID_COUNTER

        self._owner = owner
        self._fa_icons = fa_icons

        self._size = size

    @property
    def size(self) -> int | None:
        return self._size

    @size.setter
    def size(self, value):
        if not isinstance(value, int):
            raise TypeError
        self._size = value

    @property
    def owner(self) -> PlotArea | Figure:
        return self._owner

    def update(self):
        pass
