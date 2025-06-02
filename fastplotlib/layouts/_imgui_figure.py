from __future__ import annotations
from collections.abc import Callable
from functools import partial
from pathlib import Path
from typing import Literal, Iterable

import numpy as np

import imgui_bundle
from imgui_bundle import imgui, icons_fontawesome_6 as fa

from wgpu.utils.imgui import ImguiRenderer, Stats
from rendercanvas import BaseRenderCanvas

import pygfx

from ._figure import Figure
from ..ui import EdgeWindow, SubplotToolbar, StandardRightClickMenu, Popup, GUI_EDGES
from ..ui import ColormapPicker


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
        show_tooltips: bool = False,
    ):
        self._guis: dict[str, EdgeWindow] = {k: None for k in GUI_EDGES}

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
            show_tooltips=show_tooltips,
        )

        self._imgui_renderer = ImguiRenderer(self.renderer.device, self.canvas)

        fronts_path = str(
            Path(imgui_bundle.__file__).parent.joinpath(
                "assets", "fonts", "Font_Awesome_6_Free-Solid-900.otf"
            )
        )

        io = imgui.get_io()

        self._fa_icons = io.fonts.add_font_from_file_ttf(
            fronts_path, 16, glyph_ranges_as_int_list=[fa.ICON_MIN_FA, fa.ICON_MAX_FA]
        )

        io.fonts.build()
        self.imgui_renderer.backend.create_fonts_texture()

        self.imgui_renderer.set_gui(self._draw_imgui)

        self._subplot_toolbars: np.ndarray[SubplotToolbar] = np.empty(
            shape=self._subplots.size, dtype=object
        )

        for i, subplot in enumerate(self._subplots.ravel()):
            toolbar = SubplotToolbar(subplot=subplot, fa_icons=self._fa_icons)
            self._subplot_toolbars[i] = toolbar

        self._right_click_menu = StandardRightClickMenu(
            figure=self, fa_icons=self._fa_icons
        )

        self._popups: dict[str, Popup] = {}

        self.imgui_show_fps = False
        self._stats = Stats(self.renderer.device, self.canvas)

        self.register_popup(ColormapPicker)

    @property
    def guis(self) -> dict[str, EdgeWindow]:
        """GUI windows added to the Figure"""
        return self._guis

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
        imgui.new_frame()

        for subplot, toolbar in zip(
            self._subplots.ravel(), self._subplot_toolbars.ravel()
        ):
            if not subplot.toolbar:
                # if subplot.toolbar is False
                continue
            toolbar.update()

        for gui in self.guis.values():
            if gui is not None:
                gui.draw_window()

        for popup in self._popups.values():
            popup.update()

        self._right_click_menu.update()

        imgui.end_frame()

        imgui.render()

        return imgui.get_draw_data()

    def add_gui(
        self,
        gui: EdgeWindow = None,
        location: Literal["right", "bottom"] = "right",
        title="GUI Window",
        size: int = 200,
        window_flags: imgui.WindowFlags_ = imgui.WindowFlags_.no_collapse
        | imgui.WindowFlags_.no_resize,
    ):
        """
        Add a GUI to the Figure. GUIs can be added to the left or bottom edge.

        Can also be used as a decorator, see examples docstring and examples gallery.

        For a list of imgui elements see: https://pyimgui.readthedocs.io/en/latest/reference/imgui.core.html#imgui.core.begin_combo

        Note that the API docs for ``pyimgui`` do not match up exactly with ``imgui-bundle`` which we use in
        fastplotlib. Unfortunately the API docs for imgui-bundle are nonexistent (as far as we know). See the
        "imgui" section in the docs User Guide which includes tips on how to develop imgui UIs.

        Parameters
        ----------
        gui: EdgeWindow
            A GUI EdgeWindow instance, if not decorating

        location: str, "right" | "bottom"
            window location, used if decorating

        title: str
            window title, used if decorating

        size: int
            width or height of the window depending on location, used if decorating

        window_flags: imgui.WindowFlags_, default imgui.WindowFlags_.no_collapse | imgui.WindowFlags_.no_resize,
            imgui.WindowFlags_ enum, used if decorating

        Examples
        --------

        As a decorator::

            import numpy as np
            import fastplotlib as fpl
            from imgui_bundle import imgui

            figure = fpl.Figure()
            figure[0, 0].add_line(np.random.rand(100))


            @figure.add_gui(location="right", title="yay", size=100)
            def gui(fig): # figure is the only argument, so you can use it within the local scope of the GUI function
                if imgui.button("reset data"):
                    fig[0, 0].graphics[0].data[:, 1] = np.random.rand(100)

            figure.show(maintain_aspect=False)

        Subclass EdgeWindow::

            import numpy as np
            import fastplotlib as fpl
            from fastplotlib.ui import EdgeWindow

            figure = fpl.Figure()
            figure[0, 0].add_line(np.sin(np.linspace(0, np.pi * 4, 0.1)), name="sine")

            class GUI(EdgeWindow):
                def __init__(self, figure, location="right", size=200, title="My GUI", amplitude=1.0)
                    self._figure = figure

                    self._amplitude = 1

                def compute_data(self):
                    ampl = self._amplitude
                    new_data = ampl * np.sin(np.linspace(0, np.pi * 4, 0.1))
                    self._figure[0, 0]["sine"].data[:, 1] = new_data

                def update(self):
                    # gui update function
                    changed, amplitude = imgui.slider_float("amplitude", v=self._amplitude, v_max=10, v_min=0.1)
                    if changed:
                        self._amplitude = amplitude
                        self.compute_data()

            # create GUI instance and add to the figure
            gui = GUI(figure)
            figure.add_gui(gui)

        """

        def decorator(_gui: EdgeWindow | Callable):
            if location not in GUI_EDGES:
                raise ValueError(
                    f"GUI does not have a valid location, valid locations are: {GUI_EDGES}, you have passed: {location}"
                )

            if self.guis[location] is not None:
                raise ValueError(
                    f"GUI already exists in the desired location: {location}"
                )

            if not isinstance(gui, EdgeWindow):
                # being used as a decorator, create an EdgeWindow
                edge_window = EdgeWindow(
                    figure=self,
                    size=size,
                    location=location,
                    title=title,
                    update_call=partial(
                        _gui, self
                    ),  # provide figure instance in scope of the gui function
                    window_flags=window_flags,
                )
                window_location = location  # creating this reference is required
            else:
                edge_window = _gui  # creating this reference is required
                window_location = location  # creating this reference is required

            # store the gui
            self.guis[window_location] = edge_window

            # redo the layout
            self._fpl_reset_layout()

            # return function being decorated
            return _gui

        if not isinstance(gui, EdgeWindow):
            # if decorating
            return decorator

        # if not decorating
        decorator(gui)

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

        for edge in ["right"]:
            if self.guis[edge]:
                width -= self._guis[edge].size

        for edge in ["bottom"]:
            if self.guis[edge]:
                height -= self._guis[edge].size

        return 0, 0, max(1, width), max(1, height)

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
