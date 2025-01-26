from typing import Literal
import numpy as np

from imgui_bundle import imgui

from ..layouts._figure import Figure


GUI_EDGES = ["top", "right", "bottom", "left"]


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
    """Base class for imgui windows drawn within Figures"""

    pass


class EdgeWindow(Window):
    def __init__(
        self,
        figure: Figure,
        size: int,
        location: Literal["top", "bottom", "left", "right"],
        title: str,
        window_flags: int = imgui.WindowFlags_.no_collapse
        | imgui.WindowFlags_.no_resize,
        *args,
        **kwargs,
    ):
        """
        A base class for imgui windows displayed at one of the four edges of a Figure

        Parameters
        ----------
        figure: Figure
            Figure instance that this window will be placed in

        size: int
            width or height of the window, depending on its location

        location: str, "top" | "bottom" | "left" | "right"
            location of the window

        title: str
            window title

        window_flags: int
            window flag enum, valid flags are:

            .. code-block:: py

                imgui.WindowFlags_.no_title_bar
                imgui.WindowFlags_.no_resize
                imgui.WindowFlags_.no_move
                imgui.WindowFlags_.no_scrollbar
                imgui.WindowFlags_.no_scroll_with_mouse
                imgui.WindowFlags_.no_collapse
                imgui.WindowFlags_.always_auto_resize
                imgui.WindowFlags_.no_background
                imgui.WindowFlags_.no_saved_settings
                imgui.WindowFlags_.no_mouse_inputs
                imgui.WindowFlags_.menu_bar
                imgui.WindowFlags_.horizontal_scrollbar
                imgui.WindowFlags_.no_focus_on_appearing
                imgui.WindowFlags_.no_bring_to_front_on_focus
                imgui.WindowFlags_.always_vertical_scrollbar
                imgui.WindowFlags_.always_horizontal_scrollbar
                imgui.WindowFlags_.no_nav_inputs
                imgui.WindowFlags_.no_nav_focus
                imgui.WindowFlags_.unsaved_document
                imgui.WindowFlags_.no_docking
                imgui.WindowFlags_.no_nav
                imgui.WindowFlags_.no_decoration
                imgui.WindowFlags_.no_inputs

        *args
            additional args for the GUI

        **kwargs
            additional kwargs for teh GUI
        """
        super().__init__()

        if location not in GUI_EDGES:
            f"GUI does not have a valid location, valid locations are: {GUI_EDGES}, you have passed: {location}"

        self._figure = figure
        self._size = size
        self._location = location
        self._title = title
        self._window_flags = window_flags
        self._fa_icons = self._figure._fa_icons

        self._x, self._y, self._width, self._height = self.get_rect()

        self._figure.canvas.add_event_handler(self._set_rect, "resize")

    @property
    def size(self) -> int | None:
        """width or height of the edge window"""
        return self._size

    @size.setter
    def size(self, value):
        if not isinstance(value, int):
            raise TypeError
        self._size = value

    @property
    def location(self) -> str:
        """location of the window"""
        return self._location

    @property
    def x(self) -> int:
        """canvas x position of the window"""
        return self._x

    @property
    def y(self) -> int:
        """canvas y position of the window"""
        return self._y

    @property
    def width(self) -> int:
        """with the window"""
        return self._width

    @property
    def height(self) -> int:
        """height of the window"""
        return self._height

    def _set_rect(self, *args):
        self._x, self._y, self._width, self._height = self.get_rect()

    def get_rect(self) -> tuple[int, int, int, int]:
        """
        Compute the rect that defines the area this GUI is drawn to

        Returns
        -------
        int, int, int, int
            x_pos, y_pos, width, height

        """

        width_canvas, height_canvas = self._figure.canvas.get_logical_size()

        match self._location:
            case "top":
                x_pos, y_pos = (0, 0)
                width, height = (width_canvas, self.size)

            case "bottom":
                x_pos = 0
                y_pos = height_canvas - self.size
                width, height = (width_canvas, self.size)

            case "right":
                x_pos, y_pos = (width_canvas - self.size, 0)

                if self._figure.guis["top"]:
                    # if there is a GUI in the top edge, make this one below
                    y_pos += self._figure.guis["top"].size

                width, height = (self.size, height_canvas)
                if self._figure.guis["bottom"] is not None:
                    height -= self._figure.guis["bottom"].size

            case "left":
                x_pos, y_pos = (0, 0)
                if self._figure.guis["top"]:
                    # if there is a GUI in the top edge, make this one below
                    y_pos += self._figure.guis["top"].size

                width, height = (self.size, height_canvas)
                if self._figure.guis["bottom"] is not None:
                    height -= self._figure.guis["bottom"].size

        return x_pos, y_pos, width, height

    def draw_window(self):
        """helps simplify using imgui by managing window creation & position, and pushing/popping the ID"""
        # window position & size
        imgui.set_next_window_size((self.width, self.height))
        imgui.set_next_window_pos((self.x, self.y))
        flags = self._window_flags

        # begin window
        imgui.begin(self._title, p_open=None, flags=flags)

        # push ID to prevent conflict between multiple figs with same UI
        imgui.push_id(self._id_counter)

        # draw stuff from subclass into window
        self.update()

        # pop ID
        imgui.pop_id()

        # end the window
        imgui.end()

    def update(self):
        """Implement your GUI here and it will be drawn within the window. See the GUI examples"""
        raise NotImplementedError


class Popup(BaseGUI):
    def __init__(self, figure: Figure, *args, **kwargs):
        """
        Base class for creating ImGUI popups within Figures

        Parameters
        ----------
        figure: Figure
            Figure instance
        *args
            any args to pass to subclass constructor

        **kwargs
            any kwargs to pass to subclass constructor
        """

        super().__init__()

        self._figure = figure
        self._fa_icons = self._figure._fa_icons

        self.is_open = False

    def open(self, pos: tuple[int, int], *args, **kwargs):
        """implement in subclass"""
        raise NotImplementedError
