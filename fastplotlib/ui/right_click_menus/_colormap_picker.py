import ctypes

import numpy as np
import cmap

import wgpu
from imgui_bundle import imgui
from wgpu import GPUTexture

from .. import Popup
from ...utils.functions import (
    COLORMAP_NAMES,
    SEQUENTIAL_CMAPS,
    CYCLIC_CMAPS,
    DIVERGING_CMAPS,
    MISC_CMAPS,
)

all_cmaps = [*SEQUENTIAL_CMAPS, *CYCLIC_CMAPS, *DIVERGING_CMAPS, *MISC_CMAPS]


class ColormapPicker(Popup):
    """Colormap picker menu popup tool"""

    # name used to trigger this popup after it has been registered with a Figure
    name = "colormap-picker"

    def __init__(self, figure):
        super().__init__(figure=figure)

        self.renderer = self._figure.renderer
        self.imgui_renderer = self._figure.imgui_renderer

        # maps str cmap names -> int texture IDs
        self._cmap_texture_refs: dict[str, imgui.ImTextureRef] = dict()

        # make all colormaps and upload representative texture for each cmap to the GPU
        for name in all_cmaps:
            # get data that represents cmap
            colormap = cmap.Colormap(name)
            data = colormap(np.linspace(0, 1)) * 255

            # needs to be 2D to create a texture
            data = np.vstack([[data]] * 2).astype(np.uint8)

            # upload the texture to the GPU, get the texture ID and texture
            self._cmap_texture_refs[name] = self._create_texture_and_upload(data)

        # used to set the states of the UI
        self._lut_tool = None
        self._pos: tuple[int, int] = -1, -1
        self._open_new: bool = False

        self.is_open = False

        self._popup_state = "never-opened"

        self._texture_height = None

    def _create_texture_and_upload(self, data: np.ndarray) -> tuple[int, GPUTexture]:
        """crates a GPUTexture from the 2D data and uploads it"""

        # create a GPUTexture
        texture = self.renderer.device.create_texture(
            size=(data.shape[1], data.shape[0], 4),
            usage=wgpu.TextureUsage.COPY_DST | wgpu.TextureUsage.TEXTURE_BINDING,
            dimension=wgpu.TextureDimension.d2,
            format=wgpu.TextureFormat.rgba8unorm,
            mip_level_count=1,
            sample_count=1,
        )

        # upload to the GPU
        self.renderer.device.queue.write_texture(
            {"texture": texture, "mip_level": 0, "origin": (0, 0, 0)},
            data,
            {"offset": 0, "bytes_per_row": data.shape[1] * 4},
            (data.shape[1], data.shape[0], 1),
        )

        # get a view
        texture_view = texture.create_view()

        # return texture ref
        return self.imgui_renderer.backend.register_texture(texture_view)

    def open(self, pos: tuple[int, int], lut_tool):
        """
        Request that the popup be opened on the next render cycle

        Parameters
        ----------
        pos: int, int
            (x, y) position

        lut_tool: HistogramLUTTool
            instance of the LUT tool

        Returns
        -------

        """
        self._lut_tool = lut_tool

        self._pos = pos

        self._open_new = True

    def close(self):
        """cleanup after popup has closed"""
        self._lut_tool = None
        self._open_new = False
        self._pos = -1, -1

        self.is_open = False

    def _add_cmap_menu_item(self, cmap_name: str):
        # white border around cmap image
        imgui.push_style_color(imgui.Col_.border, (1.0, 1.0, 1.0, 1.0))
        imgui.push_style_var(imgui.StyleVar_.image_border_size, 1.0)

        # cmap image
        texture_ref = self._cmap_texture_refs[cmap_name]
        imgui.image(
            texture_ref,
            image_size=(50, self._texture_height),
        )
        # pop white border
        imgui.pop_style_var()
        imgui.pop_style_color()

        imgui.same_line()

        clicked, selected = imgui.selectable(
            label=cmap_name,
            p_selected=cmap_name == self._lut_tool.cmap,
        )

        if clicked and selected:
            self._lut_tool.cmap = cmap_name

    def update(self):
        if self._open_new:
            # new popup has been triggered by a LUT tool
            self._open_new = False

            imgui.set_next_window_pos(self._pos)
            imgui.open_popup("cmap-picker")

        if imgui.begin_popup("cmap-picker"):
            self.is_open = True

            # make the cmap image height the same as the text height
            self._texture_height = (imgui.get_font_size()) - 2

            if imgui.menu_item("Reset vmin-vmax", "", False)[0]:
                self._lut_tool.image_graphic.reset_vmin_vmax()

            # add all the cmap options
            for cmap_type in COLORMAP_NAMES.keys():
                if cmap_type == "qualitative":
                    continue

                imgui.separator()
                imgui.text(cmap_type.capitalize())

                for cmap_name in COLORMAP_NAMES[cmap_type]:
                    self._add_cmap_menu_item(cmap_name)

            imgui.end_popup()

        else:
            # popup went from open to closed
            if self.is_open == True:
                self.close()
