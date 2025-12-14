import enum
from typing import Literal
import numpy as np

from imgui_bundle import imgui

from ..layouts._figure import Figure


# width of the collapse/expand button (calculated to fit unicode arrow + minimal padding)
# unicode triangle char is ~8px wide, plus 2px padding each side = 12px
COLLAPSE_BUTTON_WIDTH = 12
COLLAPSE_BUTTON_HEIGHT = 24


GUI_EDGES = ["right", "bottom"]


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
        location: Literal["bottom", "right"],
        title: str,
        window_flags: enum.IntFlag = imgui.WindowFlags_.no_collapse
        | imgui.WindowFlags_.no_resize,
        *args,
        **kwargs,
    ):
        """
        A base class for imgui windows displayed at the bottom or top edge of a Figure

        Parameters
        ----------
        figure: Figure
            Figure instance that this window will be placed in

        size: int
            width or height of the window, depending on its location

        location: str, "bottom" | "right"
            location of the window

        title: str
            window title

        window_flags: enum.IntFlag
            Window flag enum, can be compared with ``|`` operator. Valid flags are:

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

        # collapse state for right-side GUI panels
        # TODO: other sides when they're supported
        self._collapsed = False

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

    @property
    def collapsed(self) -> bool:
        """whether the window is collapsed, only applicable to right-side GUI"""
        return self._collapsed

    @collapsed.setter
    def collapsed(self, value: bool):
        if not isinstance(value, bool):
            raise TypeError(f"{self.__class__.__name__}.collapsed must be a <bool>")

        # TODO: Do we want image sliders to be collapsable
        #       Need to update this when other edges are supported.
        if self._location != "right":
            return

        self._collapsed = value
        self._set_rect()

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
            case "bottom":
                x_pos = 0
                y_pos = height_canvas - self.size
                width, height = (width_canvas, self.size)

            case "right":
                # GUI panel starts after the collapse button area
                x_pos, y_pos = (width_canvas - self.size, 0)
                width, height = (self.size, height_canvas)

                if self._figure.guis["bottom"] is not None:
                    height -= self._figure.guis["bottom"].size

        return x_pos, y_pos, width, height

    def draw_window(self):
        """helps simplify using imgui by managing window creation & position, and pushing/popping the ID"""
        if self._location == "right" and self._collapsed:
            self._draw_expand_button()
            return

        if self._location == "right":
            self._draw_collapse_button()

        # window position & size
        x, y, w, h = self.get_rect()
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

    def _draw_collapse_button(self):
        """draw collapse button in the reserved area between plot and GUI panel"""
        width_canvas, height_canvas = self._figure.canvas.get_logical_size()

        # account for bottom GUI if present
        if self._figure.guis["bottom"] is not None:
            height_canvas -= self._figure.guis["bottom"].size

        # exact position: right edge of plot area, vertically centered
        # plot area ends at: width_canvas - gui_size - COLLAPSE_BUTTON_WIDTH
        # button goes from there to: width_canvas - gui_size
        x_pos = width_canvas - self._size - COLLAPSE_BUTTON_WIDTH
        y_pos = (height_canvas - COLLAPSE_BUTTON_HEIGHT) / 2

        # remove all window padding so position is exact
        imgui.push_style_var(imgui.StyleVar_.window_padding, (0, 0))

        imgui.set_next_window_pos((x_pos, y_pos))
        imgui.set_next_window_size((COLLAPSE_BUTTON_WIDTH, COLLAPSE_BUTTON_HEIGHT))

        flags = (
            imgui.WindowFlags_.no_title_bar
            | imgui.WindowFlags_.no_resize
            | imgui.WindowFlags_.no_move
            | imgui.WindowFlags_.no_scrollbar
            | imgui.WindowFlags_.no_collapse
            | imgui.WindowFlags_.no_background
        )

        imgui.begin(f"collapse-{self._title}", p_open=None, flags=flags)
        imgui.push_id(self._id_counter + 1000)

        # frame_padding: (horizontal, vertical) padding inside the button around text
        # button size = text_size + frame_padding * 2
        # we want button to fill window exactly: 12x24
        # text is ~8x14, so frame_padding = (2, 5) gives 8+4=12 width, 14+10=24 height
        imgui.push_style_var(imgui.StyleVar_.frame_padding, (2, 5))

        # transparent button, visible on hover
        imgui.push_style_color(imgui.Col_.button, (0, 0, 0, 0))
        imgui.push_style_color(imgui.Col_.button_hovered, (0.5, 0.5, 0.5, 0.5))
        imgui.push_style_color(imgui.Col_.button_active, (0.6, 0.6, 0.6, 0.6))

        if imgui.button("▶"):
            self._collapsed = True
            self._set_rect()

        imgui.pop_style_color(3)
        imgui.pop_style_var(1)

        if imgui.is_item_hovered(0):
            imgui.set_tooltip("collapse")

        imgui.pop_id()
        imgui.end()
        imgui.pop_style_var(1)  # window_padding

    def _draw_expand_button(self):
        """draw expand button at right edge when collapsed"""
        width_canvas, height_canvas = self._figure.canvas.get_logical_size()

        # account for bottom GUI if present
        if self._figure.guis["bottom"] is not None:
            height_canvas -= self._figure.guis["bottom"].size

        # exact position: flush with right edge of canvas, vertically centered
        x_pos = width_canvas - COLLAPSE_BUTTON_WIDTH
        y_pos = (height_canvas - COLLAPSE_BUTTON_HEIGHT) / 2

        # remove all window padding so position is exact
        imgui.push_style_var(imgui.StyleVar_.window_padding, (0, 0))

        imgui.set_next_window_pos((x_pos, y_pos))
        imgui.set_next_window_size((COLLAPSE_BUTTON_WIDTH, COLLAPSE_BUTTON_HEIGHT))

        flags = (
            imgui.WindowFlags_.no_title_bar
            | imgui.WindowFlags_.no_resize
            | imgui.WindowFlags_.no_move
            | imgui.WindowFlags_.no_scrollbar
            | imgui.WindowFlags_.no_collapse
            | imgui.WindowFlags_.no_background
        )

        imgui.begin(f"expand-{self._title}", p_open=None, flags=flags)
        imgui.push_id(self._id_counter)

        # same frame_padding as collapse button for exact same size
        imgui.push_style_var(imgui.StyleVar_.frame_padding, (2, 5))

        # visible button - needs to stand out when panel is collapsed
        imgui.push_style_color(imgui.Col_.button, (0.4, 0.4, 0.4, 0.9))
        imgui.push_style_color(imgui.Col_.button_hovered, (0.5, 0.5, 0.5, 1.0))
        imgui.push_style_color(imgui.Col_.button_active, (0.6, 0.6, 0.6, 1.0))

        if imgui.button("◀"):
            self._collapsed = False
            self._set_rect()

        imgui.pop_style_color(3)
        imgui.pop_style_var(1)

        if imgui.is_item_hovered(0):
            imgui.set_tooltip("expand")

        imgui.pop_id()
        imgui.end()
        imgui.pop_style_var(1)  # window_padding

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

        self.is_open = False

    def open(self, pos: tuple[int, int], *args, **kwargs):
        """implement in subclass"""
        raise NotImplementedError
