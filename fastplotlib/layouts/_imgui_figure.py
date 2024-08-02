from pathlib import Path
from typing import Literal, Iterable

import numpy as np

import imgui_bundle
from imgui_bundle import imgui, icons_fontawesome_6 as fa

from wgpu.utils.imgui import ImguiRenderer
from wgpu.gui import WgpuCanvasBase

import pygfx

from ._figure import Figure
from ._utils import make_canvas_and_renderer
from ..ui import BaseGUI, EdgeWindow, SubplotToolbar, RightClickMenu, Popup
from ..ui import ColormapPicker


GUI_EDGES = ["top", "right", "bottom", "left"]


class ImguiFigure(Figure):
    def __init__(
        self,
        shape: tuple[int, int] = (1, 1),
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
        canvas: str | WgpuCanvasBase | pygfx.Texture = None,
        renderer: pygfx.WgpuRenderer = None,
        size: tuple[int, int] = (500, 300),
        names: list | np.ndarray = None,
    ):
        self._guis: dict[str, EdgeWindow] = {k: None for k in GUI_EDGES}

        canvas, renderer = make_canvas_and_renderer(canvas, renderer, canvas_kwargs={"size": size})
        self._imgui_renderer = ImguiRenderer(renderer.device, canvas)

        super().__init__(
            shape=shape,
            cameras=cameras,
            controller_types=controller_types,
            controller_ids=controller_ids,
            controllers=controllers,
            canvas=canvas,
            renderer=renderer,
            size=size,
            names=names,
        )

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
        self._imgui_renderer.backend.create_fonts_texture()

        self._imgui_renderer.set_gui(self._draw_imgui)

        self._subplot_toolbars: np.ndarray[SubplotToolbar] = np.empty(
            shape=self._subplots.shape, dtype=object
        )

        for subplot in self._subplots.ravel():
            toolbar = SubplotToolbar(subplot=subplot, fa_icons=self._fa_icons)
            self._subplot_toolbars[subplot.position] = toolbar

        self._right_click_menu = RightClickMenu(figure=self, fa_icons=self._fa_icons)

        self._popups: dict[str, Popup] = {}

        self.register_popup(ColormapPicker)

    @property
    def guis(self) -> dict[str, EdgeWindow]:
        return self._guis

    @property
    def imgui_renderer(self) -> ImguiRenderer:
        return self._imgui_renderer

    def render(self, draw=False):
        super().render(draw)

        self.imgui_renderer.render()
        self.canvas.request_draw()

    def _draw_imgui(self) -> imgui.ImDrawData:
        imgui.new_frame()

        for toolbar in self._subplot_toolbars.ravel():
            toolbar.update()

        for gui in self.guis.values():
            if gui is not None:
                gui.update()

        for popup in self._popups.values():
            popup.update()

        self._right_click_menu.update()

        imgui.end_frame()

        imgui.render()

        return imgui.get_draw_data()

    def set_gui(self, edge: str, gui: EdgeWindow):
        if edge not in GUI_EDGES:
            raise ValueError

        if self.guis[edge] is not None:
            raise ValueError

        if not isinstance(gui, BaseGUI):
            raise TypeError

        self.guis[edge] = gui

        self.set_gui_size(edge, gui.size)

    def set_gui_size(self, edge: str, size: int):
        if self.guis[edge] is None:
            raise ValueError

        self.guis[edge].size = size

    def get_pygfx_render_area(self, *args):
        """update size of fastplotlib managed, i.e. non-imgui, part of canvas"""
        width, height = self.canvas.get_logical_size()

        for edge in ["left", "right"]:
            if self.guis[edge]:
                width -= self._guis[edge].size

        for edge in ["top", "bottom"]:
            if self.guis[edge]:
                height -= self._guis[edge].size

        if self.guis["left"]:
            xpos = self.guis["left"].size
        else:
            xpos = 0

        if self.guis["top"]:
            ypos = self.guis["top"].size
        else:
            ypos = 0

        return [xpos, ypos, width, height]

    def _reset_viewports(self):
        # TODO: think about moving this to Figure later,
        #  maybe also refactor Subplot and PlotArea so that
        #  the resize event is handled at the Figure level instead
        for subplot in self:
            subplot.set_viewport_rect()
            for dock in subplot.docks.values():
                dock.set_viewport_rect()

    def register_popup(self, popup: Popup.__class__):
        self._popups[popup.name] = popup(self)

    def open_popup(self, name, pos: tuple[int, int], **kwargs):
        if self._popups[name].is_open:
            return

        self._popups[name].open(pos, **kwargs)
