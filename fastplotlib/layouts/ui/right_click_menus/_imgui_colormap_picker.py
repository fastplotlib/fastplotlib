from pathlib import Path
import ctypes

import numpy as np

import wgpu
from imgui_bundle import imgui
from wgpu import GPUTexture

from .. import Popup
from ....utils import colormaps


cmap_paths = sorted(Path(colormaps.__file__).absolute().parent.glob("*"))


# TODO: create and upload textures only once per Figure
class ColormapPicker(Popup):
    name = "colormap-picker"

    def __init__(self, figure):
        # TODO: we actually don't need figure for this, maybe another simpler base class for popups?
        super().__init__(figure=figure, fa_icons=None)

        self.renderer = self._figure.renderer
        self.imgui_renderer = self._figure.imgui_renderer

        # linear interpolation sampler to nicely display the cmaps
        self.texture_sampler = self.renderer.device.create_sampler(
            label="img-sampler",
            mag_filter=wgpu.FilterMode.linear,
            min_filter=wgpu.FilterMode.linear,
            mipmap_filter=wgpu.FilterMode.linear,
        )

        self._texture_ids: dict[str, int] = {}
        self._textures = list()

        # make all colormaps and upload representative texture for each to the GPU
        for path in cmap_paths:
            if not path.is_file():
                continue

            data = np.loadtxt(path).T
            data = np.vstack([[data]] * 2).astype(np.uint8)
            if data.size < 1:
                continue  # skip any files that are not cmaps in here

            name = path.name

            self._texture_ids[name], texture = self._create_texture_and_upload(data)
            self._textures.append(texture)

        self._lut_tool = None
        self._pos: tuple[int, int] = -1, -1
        self._open_new: bool = False

        self.is_open = False

        self._popup_state = "never-opened"

    def _create_texture_and_upload(self, data: np.ndarray) -> tuple[int, GPUTexture]:
        # crates a GPUTexture and uploads it

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

        # get the id so that imgui can display it
        id_texture = ctypes.c_int32(id(texture_view)).value
        # add texture view to the backend so that it can be retrieved for rendering
        self.imgui_renderer.backend._texture_views[id_texture] = texture_view

        return id_texture, texture

    def open(self, pos: tuple[int, int], lut_tool):
        self._lut_tool = lut_tool

        self._pos = pos

        self._open_new = True

    def close(self):
        self._lut_tool = None
        self._open_new = False
        self._pos = -1, -1

        self.is_open = False

        self.clear_event_filters()

    def update(self):
        if self._open_new:
            # new popup has been triggered by a LUT tool
            self._open_new = False

            imgui.set_next_window_pos(self._pos, imgui.Cond_.appearing)
            imgui.open_popup("cmap-picker")

        if imgui.begin_popup("cmap-picker"):
            texture_height = (self.imgui_renderer.backend.io.font_global_scale * imgui.get_font().font_size) - 2

            self.is_open = True
            if imgui.menu_item("reset vmin-vmax", None, False)[0]:
                self._lut_tool.image_graphic.reset_vmin_vmax()

            for cmap_name, texture_id in self._texture_ids.items():
                clicked, selected = imgui.menu_item(
                    label=cmap_name, shortcut=None, p_selected=self._lut_tool.cmap == cmap_name
                )

                imgui.same_line()
                imgui.image(texture_id, image_size=(50, texture_height), border_col=(1, 1, 1, 1))

                if clicked and selected:
                    self._lut_tool.cmap = cmap_name

            self.set_event_filter("cmap-picker-filter")

            imgui.end_popup()

        else:
            # popup went from open to closed
            if self.is_open == True:
                self.close()
