from __future__ import annotations
from collections.abc import Callable
from pathlib import Path
from typing import Literal, Iterable

import numpy as np

import imgui_bundle
from imgui_bundle import imgui, icons_fontawesome_6 as fa

from wgpu.utils.imgui import ImguiRenderer, Stats
from rendercanvas import BaseRenderCanvas

import pygfx

from ._figure import Figure
from ._rect import RectManager
from ._utils import IMGUI_TOOLBAR_HEIGHT
from ..ui import ImguiWindow, ImguiPopup, SubplotToolbar, StandardRightClickMenu, EDGES
from ..ui._base import _wrap_update_call


class ImguiFigure(Figure):
    def __init__(
        self,
        shape: tuple[int, int] = (1, 1),
        rects: list[tuple | np.ndarray] = None,
        extents: list[tuple | np.ndarray] = None,
        cameras: (
            Literal["2d", "3d"]
            | Iterable[Iterable[Literal["2d", "3d"]]]
            | pygfx.PerspectiveCamera
            | Iterable[Iterable[pygfx.PerspectiveCamera]]
        ) = "2d",
        controller_types: (
            Iterable[Iterable[Literal["panzoom", "fly", "trackball", "orbit"]]]
            | Iterable[Literal["panzoom", "fly", "trackball", "orbit"]]
        ) = None,
        controller_ids: (
            Literal["sync"]
            | Iterable[int]
            | Iterable[Iterable[int]]
            | Iterable[Iterable[str]]
        ) = None,
        controllers: pygfx.Controller | Iterable[Iterable[pygfx.Controller]] = None,
        canvas: str | BaseRenderCanvas | pygfx.Texture = None,
        renderer: pygfx.WgpuRenderer = None,
        canvas_kwargs: dict = None,
        size: tuple[int, int] = (500, 300),
        names: list | np.ndarray = None,
    ):
        # edge windows reserve canvas space, keyed by location; floating windows draw over the plots
        self._edge_windows: dict[str, ImguiWindow] = {loc: None for loc in EDGES}
        self._floating_windows: list[ImguiWindow] = []

        # figure level right-click popup, and the popup opened by the most recent right-click
        self._imgui_right_click: ImguiPopup = None
        self._currently_open_imgui_right_click: ImguiPopup = None

        self._right_click_press_pos: imgui.ImVec2 = None

        super().__init__(
            shape=shape,
            rects=rects,
            extents=extents,
            cameras=cameras,
            controller_types=controller_types,
            controller_ids=controller_ids,
            controllers=controllers,
            canvas=canvas,
            renderer=renderer,
            canvas_kwargs=canvas_kwargs,
            size=size,
            names=names,
        )

        self._imgui_renderer = ImguiRenderer(self.renderer.device, self.canvas)

        # This loads both the Roboto Font and FontAwesome 6 icons and creates and merged font
        # allowing us to use both without pushing and popping to display icons or regular text
        sans_serif_font = str(
            Path(imgui_bundle.__file__).parent.joinpath(
                "assets", "fonts", "Roboto", "Roboto-Regular.ttf"
            )
        )

        fa_6_fonts_path = str(
            Path(imgui_bundle.__file__).parent.joinpath(
                "assets", "fonts", "Font_Awesome_6_Free-Solid-900.otf"
            )
        )

        io = imgui.get_io()

        self._default_imgui_font = io.fonts.add_font_from_file_ttf(
            sans_serif_font, 14, imgui.ImFontConfig()
        )

        font_config = imgui.ImFontConfig()
        font_config.merge_mode = True

        self._default_imgui_font = io.fonts.add_font_from_file_ttf(
            fa_6_fonts_path,
            14,
            font_config,
        )

        imgui.push_font(self._default_imgui_font, self._default_imgui_font.legacy_size)

        self.imgui_renderer.set_gui(self._draw_imgui)

        for subplot in self._subplots.ravel():
            subplot.add_imgui_window(
                SubplotToolbar(), location="toolbar", size=IMGUI_TOOLBAR_HEIGHT
            )

        self.set_imgui_right_click(StandardRightClickMenu())

        self.imgui_show_fps = False
        self._stats = Stats(self.renderer.device, self.canvas)

    @property
    def default_imgui_font(self) -> imgui.ImFont:
        return self._default_imgui_font

    @property
    def imgui_windows(self) -> dict[str, ImguiWindow]:
        """edge imgui windows added to the Figure, keyed by location"""
        return self._edge_windows

    @property
    def imgui_renderer(self) -> ImguiRenderer:
        """imgui renderer"""
        return self._imgui_renderer

    def _render(self, draw=False):
        if self.imgui_show_fps:
            with self._stats:
                super()._render(draw)
        else:
            super()._render(draw)

        self.imgui_renderer.render()

        # needs to be here else events don't get processed
        self.canvas.request_draw()

    def _draw_imgui(self) -> imgui.ImDrawData:
        # figure-level windows: edge windows then floating windows
        for window in (*self._edge_windows.values(), *self._floating_windows):
            if window is None:
                continue
            self._layout_imgui_window(window)
            window.draw()

        # subplot windows, edge window rects are set by Frame.reset_viewport
        for subplot in self._subplots.ravel():
            for location, window in subplot.imgui_windows.items():
                if window is None:
                    continue
                if location == "toolbar" and not subplot.toolbar:
                    continue
                window.draw()

        self._fpl_handle_right_click()

        # the currently open popup is drawn first, opening it closes any other popup that is still open.
        # it keeps being drawn after it closes so that it can also draw its own windows
        popup = self._currently_open_imgui_right_click
        if popup is not None:
            popup.draw()

        if self._imgui_right_click is not None and self._imgui_right_click is not popup:
            self._imgui_right_click.draw()

    def add_imgui_window(
        self,
        window: ImguiWindow = None,
        *,
        location: Literal["left", "right", "top", "bottom", "floating"] = None,
        size: int = None,
        rect: tuple | np.ndarray = None,
        extent: tuple | np.ndarray = None,
        title: str = None,
        window_flags: imgui.WindowFlags_ = None,
    ):
        """
        Add an imgui window to the Figure. Can also be used as a decorator, see examples.

        A window can be placed on an edge ("left", "right", "top", "bottom") where it reserves canvas space so it
        does not cover the subplots, "floating" for an auto-sized draggable window, or at a fixed fractional or pixel
        ``rect`` or ``extent`` of the canvas. An existing window at an edge ``location`` is replaced.

        For a list of imgui elements see the imgui docs and the "imgui" section in the fastplotlib user guide.

        Parameters
        ----------
        window: ImguiWindow, optional
            an ``ImguiWindow`` instance, omit when decorating

        location: str, "left" | "right" | "top" | "bottom" | "floating"
            edge windows reserve canvas space, "floating" is auto-sized and draggable

        size: int
            edge window thickness in pixels, required for edge windows

        rect: (x, y, w, h), optional
            fractional or pixel rect for a fixed floating window

        extent: (xmin, xmax, ymin, ymax), optional
            fractional or pixel extent for a fixed floating window

        title: str, optional
            window title, drawn as a title bar for edge windows. If ``None`` no title bar is drawn.

        window_flags: imgui.WindowFlags_
            imgui window flags, used when decorating; if not provided, the default depends on placement — edge
            windows use ``no_collapse | no_resize | no_title_bar | no_bring_to_front_on_focus`` (custom title bar,
            stays behind overlays), floating windows use ``none`` (native title bar, collapsible and movable),
            fixed rect/extent windows use ``no_collapse | no_move | no_resize`` (native title bar)

        Examples
        --------

        As a decorator::

            import numpy as np
            import fastplotlib as fpl
            from imgui_bundle import imgui

            figure = fpl.Figure()
            figure[0, 0].add_line(np.random.rand(100))

            @figure.add_imgui_window(location="right", title="controls", size=200)
            def gui(fig):  # the figure is passed if the function takes an argument
                if imgui.button("reset data"):
                    fig[0, 0].graphics[0].data[:, 1] = np.random.rand(100)

        Instance::

            figure.add_imgui_window(MyWindow(), location="bottom", size=100)

        """

        def decorator(_window):
            if isinstance(_window, ImguiWindow):
                win = _window
            elif callable(_window):
                win = ImguiWindow(update_call=_wrap_update_call(_window, self))
            else:
                raise TypeError(
                    "add_imgui_window() must be used as a decorator on a function, or given an `ImguiWindow` instance"
                )

            win._fpl_add_hook(
                figure=self,
                subplot=None,
                location=location,
                size=size,
                rect=rect,
                extent=extent,
                title=title,
                window_flags=window_flags,
            )
            self._register_imgui_window(win)
            return _window

        if window is None:
            return decorator

        decorator(window)
        return window

    def _register_imgui_window(self, window: ImguiWindow):
        """store a figure-level window and reset the layout if it reserves canvas space"""
        location = window.location

        if location in EDGES:
            if window.size is None:
                raise ValueError(f"must provide `size` for an edge window, location: {location}")
            self._edge_windows[location] = window
            self._fpl_reset_layout()

        elif window._floating or window._rect_manager is not None:
            self._floating_windows.append(window)

        else:
            raise ValueError(
                "imgui window must have a valid `location` (an edge or 'floating'), or a `rect` or `extent`"
            )

    def append_imgui_window(self, gui: Callable = None, *, location: str = None):
        """
        Append imgui elements to an existing edge window. Can also be used as a decorator.

        Parameters
        ----------
        gui: callable, optional
            function that draws imgui elements, omit when decorating

        location: str, "left" | "right" | "top" | "bottom"
            location of the existing window to append to

        """
        if location not in EDGES:
            raise ValueError(f"valid locations to append to are: {EDGES}, you have passed: {location}")

        window = self._edge_windows[location]
        if window is None:
            raise ValueError(f"no imgui window at location to append to: {location}")

        def decorator(_gui):
            window._update_calls.append(_wrap_update_call(_gui, self))
            return _gui

        if gui is None:
            return decorator

        return decorator(gui)

    def remove_imgui_window(self, location: str) -> ImguiWindow:
        """
        Remove and return the edge imgui window at the given location

        Parameters
        ----------
        location: str
            "left" | "right" | "top" | "bottom"

        Returns
        -------
        ImguiWindow
            the removed window, it can be added again later

        """
        if location not in EDGES:
            raise ValueError(f"valid locations are: {EDGES}, you have passed: {location}")

        window = self._edge_windows[location]
        self._edge_windows[location] = None
        self._fpl_reset_layout()

        return window

    def _edge_size(self, edge: str) -> int:
        """thickness in pixels reserved by the edge window at ``edge``, 0 if none"""
        window = self._edge_windows[edge]
        return window.size if window is not None else 0

    def _layout_imgui_window(self, window: ImguiWindow):
        """compute and set the pixel rect of a figure-level imgui window"""
        if window._floating:
            # imgui auto-sizes a floating window from its content, nothing to compute
            return

        width, height = self.canvas.get_logical_size()

        if window._rect_manager is not None:
            window._rect_manager.canvas_resized((0, 0, width, height))
            window._fpl_set_rect(*(round(v) for v in window._rect_manager.rect))
            return

        # edge window, spans the full edge minus any perpendicular edge windows
        sl, sr = self._edge_size("left"), self._edge_size("right")
        st, sb = self._edge_size("top"), self._edge_size("bottom")
        mid_y, mid_h = st, height - st - sb

        match window.location:
            case "top":
                rect = (0, 0, width, st)
            case "bottom":
                rect = (0, height - sb, width, sb)
            case "left":
                rect = (0, mid_y, sl, mid_h)
            case "right":
                rect = (width - sr, mid_y, sr, mid_h)

        window._fpl_set_rect(*(round(v) for v in rect))

    def get_pygfx_render_area(self, *args) -> tuple[int, int, int, int]:
        """
        Get rect for the portion of the canvas that the pygfx renderer draws to,
        i.e. non-imgui, part of canvas

        Returns
        -------
        tuple[int, int, int, int]
            x_pos, y_pos, width, height

        """

        width, height = self.canvas.get_logical_size()

        sl, sr = self._edge_size("left"), self._edge_size("right")
        st, sb = self._edge_size("top"), self._edge_size("bottom")

        x = sl
        y = st
        width = width - sl - sr
        height = height - st - sb

        return x, y, max(1, width), max(1, height)

    @property
    def imgui_right_click(self) -> ImguiPopup | None:
        """
        The imgui popup that is opened by a right-click within a subplot, a ``StandardRightClickMenu`` by default.
        A popup set on a subplot or graphic replaces it for that subplot or graphic.
        """
        return self._imgui_right_click

    def set_imgui_right_click(
        self,
        popup: ImguiPopup | Callable = None,
        *,
        window_flags: imgui.WindowFlags_ = None,
    ):
        """
        Set the imgui popup that is opened by a right-click within a subplot, replaces the standard right-click
        menu. Can also be used as a decorator, see examples.

        For a list of imgui elements see the imgui docs and the "imgui" section in the fastplotlib user guide.

        Parameters
        ----------
        popup: ImguiPopup | callable, optional
            an ``ImguiPopup`` instance, or a function that draws imgui elements. Omit when decorating.

        window_flags: imgui.WindowFlags_, optional
            imgui window flags for the popup

        Examples
        --------

        As a decorator::

            import numpy as np
            import fastplotlib as fpl
            from imgui_bundle import imgui

            figure = fpl.Figure()
            figure[0, 0].add_line(np.random.rand(100))

            @figure.set_imgui_right_click()
            def popup(fig):  # the figure is passed if the function takes an argument
                if imgui.menu_item("autoscale", "", False)[0]:
                    fig.imgui_right_click.subplot.auto_scale()

        Function, the same function can be set on any number of figures, subplots or graphics::

            def popup(subplot):
                imgui.text(f"subplot: {subplot.name}")

            figure[0, 0].set_imgui_right_click(popup)
            figure[0, 1].set_imgui_right_click(popup)

        Instance::

            figure.set_imgui_right_click(MyPopup())

        """

        def decorator(_popup):
            if isinstance(_popup, ImguiPopup):
                p = _popup
            elif callable(_popup):
                p = ImguiPopup(update_call=_wrap_update_call(_popup, self))
            else:
                raise TypeError(
                    "set_imgui_right_click() must be used as a decorator, or given an `ImguiPopup` instance or a "
                    "function that draws imgui elements"
                )

            p._fpl_add_hook(figure=self, parent=self, window_flags=window_flags)
            self._imgui_right_click = p
            return _popup

        if popup is None:
            return decorator

        decorator(popup)
        return popup

    def append_imgui_right_click(self, gui: Callable = None):
        """
        Append imgui elements to the Figure's right-click popup, the standard right-click menu by default. Can also
        be used as a decorator.

        Parameters
        ----------
        gui: callable, optional
            function that draws imgui elements, omit when decorating

        """
        popup = self._imgui_right_click
        if popup is None:
            raise ValueError(
                "no imgui right-click popup set on this figure to append to, set one using "
                "`figure.set_imgui_right_click()`"
            )

        def decorator(_gui):
            popup._update_calls.append(_wrap_update_call(_gui, self))
            return _gui

        if gui is None:
            return decorator

        return decorator(gui)

    def remove_imgui_right_click(self) -> ImguiPopup:
        """
        Remove and return the Figure's right-click popup

        Returns
        -------
        ImguiPopup
            the removed popup, it can be set again later

        """
        popup = self._imgui_right_click
        self._imgui_right_click = None

        return popup

    def _fpl_handle_right_click(self):
        """open the popup of the graphic, subplot or Figure that was right-clicked"""
        if imgui.is_mouse_down(1):
            if self._right_click_press_pos is None:
                self._right_click_press_pos = imgui.get_mouse_pos()
            return

        press_pos = self._right_click_press_pos
        self._right_click_press_pos = None

        if press_pos is None or not imgui.is_mouse_released(1):
            return

        pos = imgui.get_mouse_pos()

        if press_pos != pos:
            # right-drag zooms the camera
            return

        if imgui.is_window_hovered(imgui.HoveredFlags_.any_window):
            # pointer is over an imgui window, not the pygfx render area
            return

        for subplot in self._subplots.ravel():
            if subplot.viewport.is_inside(pos.x, pos.y):
                break
        else:
            return

        pick_info = subplot.get_pick_info((pos.x, pos.y))
        graphic = pick_info["graphic"] if pick_info is not None else None

        # the most specific popup wins
        if graphic is not None and graphic.imgui_right_click is not None:
            popup = graphic.imgui_right_click
        elif subplot.imgui_right_click is not None:
            popup = subplot.imgui_right_click
        else:
            popup = self._imgui_right_click

        if popup is not None:
            self._fpl_open_imgui_right_click(popup, subplot=subplot, graphic=graphic)

    def _fpl_open_imgui_right_click(self, popup: ImguiPopup, subplot, graphic):
        """set the popup that is drawn as the open popup, and open it"""
        previous = self._currently_open_imgui_right_click
        if previous is not None and previous is not popup:
            previous._fpl_close()

        self._currently_open_imgui_right_click = popup
        popup._fpl_open(subplot=subplot, graphic=graphic)
