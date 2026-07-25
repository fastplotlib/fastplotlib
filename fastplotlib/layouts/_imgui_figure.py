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
from ..ui import ImguiWindow, SubplotToolbar, StandardRightClickMenu, Popup, EDGES
from ..ui import ColormapPicker
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
        std_right_click_menu: type[Popup] = StandardRightClickMenu,
    ):
        # edge windows reserve canvas space, keyed by location; floating windows draw over the plots
        self._edge_windows: dict[str, ImguiWindow] = {loc: None for loc in EDGES}
        self._floating_windows: list[ImguiWindow] = []

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

        self._std_right_click_menu = std_right_click_menu(figure=self)

        self._popups: dict[str, Popup] = {}

        self.imgui_show_fps = False
        self._stats = Stats(self.renderer.device, self.canvas)

        self.register_popup(ColormapPicker)

    @property
    def default_imgui_font(self) -> imgui.ImFont:
        return self._default_imgui_font

    @property
    def std_right_click_menu(self) -> Popup:
        return self._std_right_click_menu

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
            window.draw_window()

        # subplot windows, edge window rects are set by Frame.reset_viewport
        for subplot in self._subplots.ravel():
            for location, window in subplot.imgui_windows.items():
                if window is None:
                    continue
                if location == "toolbar" and not subplot.toolbar:
                    continue
                window.draw_window()

        for popup in self._popups.values():
            popup.update()

        self._std_right_click_menu.update()

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

    def register_popup(self, popup: Popup.__class__):
        """
        Register a popup class. Note that this takes the class, not an instance

        Parameters
        ----------
        popup: Popup subclass

        """
        self._popups[popup.name] = popup(self)

    def open_popup(self, name: str, pos: tuple[int, int], **kwargs):
        """
        Open a registered popup

        Parameters
        ----------
        name: str
            The registered name of the popup

        pos: int, int
            x_pos, y_pos for the popup

        kwargs
            any additional kwargs to pass to the Popup's open() method

        """

        if self._popups[name].is_open:
            return

        self._popups[name].open(pos, **kwargs)
