from __future__ import annotations
import inspect
from collections.abc import Callable
from functools import partial
from typing import Literal

from imgui_bundle import imgui


# edges that reserve space, ordered as they are carved from the render area
EDGES = ["left", "right", "top", "bottom"]

# all valid keyed locations, "toolbar" is subplot only, "floating" uses auto-placement
LOCATIONS = EDGES + ["toolbar", "floating"]


def _wrap_update_call(func: Callable, host) -> Callable:
    """
    Wrap an imgui draw function for use as a window update call. The host, a ``Figure`` or ``Subplot``, is passed
    as the only positional arg if the function accepts one, otherwise the function is called with no args.
    """
    params = inspect.signature(func).parameters.values()
    takes_arg = any(
        p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD, p.VAR_POSITIONAL)
        for p in params
    )
    if takes_arg:
        return partial(func, host)
    return func


def _resolve_window(window: "ImguiWindow" | Callable, host, title: str, window_flags) -> "ImguiWindow":
    """return the passed ImguiWindow instance, or create one wrapping the decorated function"""
    if isinstance(window, ImguiWindow):
        return window
    if callable(window):
        return ImguiWindow(
            title=title, window_flags=window_flags, update_call=_wrap_update_call(window, host)
        )
    raise TypeError(
        "add_imgui_window() must be used as a decorator on a function, or given an `ImguiWindow` instance"
    )


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


class ImguiWindow(BaseGUI):
    def __init__(
        self,
        title: str = "",
        window_flags: imgui.WindowFlags_ = imgui.WindowFlags_.no_collapse
        | imgui.WindowFlags_.no_resize
        | imgui.WindowFlags_.no_title_bar,
        update_call: Callable = None,
    ):
        """
        An imgui window drawn within a Figure. The placement, i.e. location and size, is managed by the host
        (a ``Figure`` or ``Subplot``) when the window is added using ``add_imgui_window()``. Subclass and implement
        ``update()`` to draw imgui elements, or pass a callable as ``update_call`` (this is what the
        ``add_imgui_window()`` decorator does).

        Parameters
        ----------
        title: str
            window title, drawn as a title bar if not empty

        window_flags: imgui.WindowFlags_
            window flag enum, can be combined with the ``|`` operator, valid flags are:

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

        update_call: callable
            a callable that draws imgui elements, used instead of ``update()`` when decorating. See ``add_imgui_window``.

        """
        super().__init__()

        self._title = title
        self._window_flags = window_flags

        # imgui element draw calls, run in order within the window on each render
        if update_call is None:
            self._update_calls = [self.update]
        else:
            self._update_calls = [update_call]

        # placement, set by the host in add_imgui_window()
        self._figure = None  # ImguiFigure, used for relayout and canvas
        self._host = None  # Figure or Subplot that owns this window
        self._location = None
        self._size = None  # edge or toolbar thickness in pixels
        self._rect_manager = None  # for fractional rect/extent placement
        self._floating = False  # auto-sized, not pinned to a rect

        # pixel rect, set by the host on each layout pass
        self._x, self._y, self._width, self._height = 0, 0, 0, 0

        # resize and collapse state, only used by resizeable edge windows
        self._resize_cursor_set = False
        self._resize_blocked = False
        self._right_gui_resizing = False
        self._separator_thickness = 14.0
        self._collapsed = False
        self._old_size = None

    @property
    def location(self) -> str:
        """location of the window"""
        return self._location

    @property
    def size(self) -> int | None:
        """edge or toolbar thickness in pixels, ``None`` for floating and fractional windows"""
        return self._size

    @size.setter
    def size(self, value: int):
        if not isinstance(value, int):
            raise TypeError(f"{self.__class__.__name__}.size must be an <int>")
        self._size = value
        # reserving windows change the layout when resized
        if self._figure is not None and self._reserves:
            self._figure._fpl_reset_layout()

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
        """width of the window"""
        return self._width

    @property
    def height(self) -> int:
        """height of the window"""
        return self._height

    @property
    def _reserves(self) -> bool:
        """whether this window reserves canvas space, i.e. edge or toolbar windows"""
        return self._location in EDGES or self._location == "toolbar"

    def _fpl_set_rect(self, x: int, y: int, width: int, height: int):
        """set the pixel rect, called by the host on each layout pass"""
        self._x, self._y, self._width, self._height = x, y, width, height

    def _draw_resize_handle(self):
        if self._location not in ("bottom", "right"):
            return

        if self._location == "bottom":
            imgui.set_cursor_pos((0, 0))
            imgui.invisible_button("##resize_handle", imgui.ImVec2(imgui.get_window_width(), self._separator_thickness))

            hovered = imgui.is_item_hovered()
            active = imgui.is_item_active()

            # Get the actual screen rect of the button after it's been laid out
            rect_min = imgui.get_item_rect_min()
            rect_max = imgui.get_item_rect_max()

        elif self._location == "right":
            imgui.set_cursor_pos((0, 0))
            screen_pos = imgui.get_cursor_screen_pos()
            win_height = imgui.get_window_height()
            mouse_pos = imgui.get_mouse_pos()

            rect_min = imgui.ImVec2(screen_pos.x, screen_pos.y)
            rect_max = imgui.ImVec2(screen_pos.x + self._separator_thickness, screen_pos.y + win_height)

            hovered = (
                rect_min.x <= mouse_pos.x <= rect_max.x
                and rect_min.y <= mouse_pos.y <= rect_max.y
            )

            if hovered and imgui.is_mouse_clicked(0):
                self._right_gui_resizing = True

            if not imgui.is_mouse_down(0):
                self._right_gui_resizing = False

            active = self._right_gui_resizing

            imgui.set_cursor_pos((self._separator_thickness, 0))

        if hovered and imgui.is_mouse_double_clicked(0):
            if not self._collapsed:
                self._old_size = self.size
                if self._location == "bottom":
                    self.size = int(self._separator_thickness)
                elif self._location == "right":
                    self.size = int(self._separator_thickness)
                self._collapsed = True
            else:
                self.size = self._old_size
                self._collapsed = False

        if hovered or active:
            if not self._resize_cursor_set:
                if self._location == "bottom":
                    self._figure.canvas.set_cursor("ns_resize")

                elif self._location == "right":
                    self._figure.canvas.set_cursor("ew_resize")

                self._resize_cursor_set = True
            imgui.set_tooltip("Drag to resize, double click to expand/collapse")

        elif self._resize_cursor_set:
            self._figure.canvas.set_cursor("default")
            self._resize_cursor_set = False

        if active and imgui.is_mouse_dragging(0):
            if self._location == "bottom":
                delta = imgui.get_mouse_drag_delta(0).y

            elif self._location == "right":
                delta = imgui.get_mouse_drag_delta(0).x

            imgui.reset_mouse_drag_delta(0)
            px, py, pw, ph = self._figure.get_pygfx_render_area()

            if self._location == "bottom":
                new_render_size = ph + delta
            elif self._location == "right":
                new_render_size = pw + delta

            # check if the new size would make the pygfx render area too small
            if (delta < 0) and (new_render_size < 150):
                print("not enough render area")
                self._resize_blocked = True

            if self._resize_blocked:
                # check if cursor has returned
                if self._location == "bottom":
                    _min, pos, _max = rect_min.y, imgui.get_mouse_pos().y, rect_max.y

                elif self._location == "right":
                    _min, pos, _max = rect_min.x, imgui.get_mouse_pos().x, rect_max.x

                if ((_min - 5) <= pos <= (_max + 5)) and delta > 0:
                    # if the mouse cursor is back on the bar and the delta > 0, i.e. render area increasing
                    self._resize_blocked = False

            if not self._resize_blocked:
                self.size = max(30, round(self.size - delta))
                self._collapsed = False

        draw_list = imgui.get_window_draw_list()

        line_color = (
            imgui.get_color_u32(imgui.ImVec4(0.9, 0.9, 0.9, 1.0))
            if (hovered or active)
            else imgui.get_color_u32(imgui.ImVec4(0.5, 0.5, 0.5, 0.8))
        )
        bg_color = (
            imgui.get_color_u32(imgui.ImVec4(0.2, 0.2, 0.2, 0.8))
            if (hovered or active)
            else imgui.get_color_u32(imgui.ImVec4(0.15, 0.15, 0.15, 0.6))
        )

        # Background bar
        draw_list.add_rect_filled(
            imgui.ImVec2(rect_min.x, rect_min.y),
            imgui.ImVec2(rect_max.x, rect_max.y),
            bg_color,
        )

        # Three grip dots centered on the line
        dot_spacing = 7.0
        dot_radius = 2
        if self._location == "bottom":
            mid_y = (rect_min.y + rect_max.y) * 0.5
            center_x = (rect_min.x + rect_max.x) * 0.5
            for i in (-1, 0, 1):
                cx = center_x + i * dot_spacing
                draw_list.add_circle_filled(imgui.ImVec2(cx, mid_y), dot_radius, line_color)

            imgui.set_cursor_pos((0, imgui.get_cursor_pos_y() - imgui.get_style().item_spacing.y))

        elif self._location == "right":
            mid_x = (rect_min.x + rect_max.x) * 0.5
            center_y = (rect_min.y + rect_max.y) * 0.5
            for i in (-1, 0, 1):
                cy = center_y + i * dot_spacing
                draw_list.add_circle_filled(
                    imgui.ImVec2(mid_x, cy), dot_radius, line_color
                )

    def _draw_title(self, title: str):
        padding = imgui.ImVec2(10, 4)
        text_size = imgui.calc_text_size(title)
        win_width = imgui.get_window_width()
        box_size = imgui.ImVec2(win_width, text_size.y + padding.y * 2)

        box_screen_pos = imgui.get_cursor_screen_pos()

        draw_list = imgui.get_window_draw_list()

        # Background — use imgui's default title bar color
        draw_list.add_rect_filled(
            imgui.ImVec2(box_screen_pos.x, box_screen_pos.y),
            imgui.ImVec2(box_screen_pos.x + box_size.x, box_screen_pos.y + box_size.y),
            imgui.get_color_u32(imgui.Col_.title_bg_active),
        )

        # Centered text
        text_pos = imgui.ImVec2(
            box_screen_pos.x + (win_width - text_size.x) * 0.5,
            box_screen_pos.y + padding.y,
        )
        draw_list.add_text(
            text_pos, imgui.get_color_u32(imgui.ImVec4(1, 1, 1, 1)), title
        )

        imgui.dummy(imgui.ImVec2(win_width, box_size.y))

    def draw_window(self):
        """helps simplify using imgui by managing window creation & position, and pushing/popping the ID"""
        # window position & size
        if self._floating:
            # floating windows are auto-sized, only set the initial position
            imgui.set_next_window_pos((self.x, self.y), imgui.Cond_.appearing)
        else:
            imgui.set_next_window_size((self.width, self.height))
            imgui.set_next_window_pos((self.x, self.y))

        # append the id to keep the window unique without changing the visible title
        imgui.begin(f"{self._title}##{self._id_counter}", p_open=None, flags=self._window_flags)

        # resize handle for right and bottom edge windows on the figure
        if self._reserves and self._host is self._figure:
            self._draw_resize_handle()

        # push ID to prevent conflict between multiple figs with same UI
        imgui.push_id(self._id_counter)

        # collapse the UI if the separator state is collapsed
        # otherwise the UI renders partially on the separator for "right" guis and it looks weird
        main_height = 1.0 if self._collapsed else 0.0
        imgui.begin_child("##main_ui", imgui.ImVec2(0, main_height))

        if self._title:
            self._draw_title(self._title)

        imgui.indent(6.0)
        # draw imgui elements from the subclass or decorated function(s)
        for update_call in self._update_calls:
            update_call()

        imgui.end_child()

        # pop ID
        imgui.pop_id()

        # end the window
        imgui.end()

    def update(self):
        """Implement your GUI here and it will be drawn within the window. See the GUI examples"""
        raise NotImplementedError


class Popup(BaseGUI):
    def __init__(self, figure, *args, **kwargs):
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
