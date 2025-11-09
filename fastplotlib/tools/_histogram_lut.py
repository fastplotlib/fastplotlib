from math import ceil
from typing import Sequence
import weakref

import numpy as np

import pygfx

from ..utils import subsample_array, RenderQueue
from ..graphics import LineGraphic, ImageGraphic, ImageVolumeGraphic, TextGraphic
from ..graphics.utils import pause_events
from ..graphics._base import Graphic
from ..graphics.features import GraphicFeatureEvent
from ..graphics.selectors import LinearRegionSelector


def _format_value(value: float):
    abs_val = abs(value)
    if abs_val < 0.01 or abs_val > 9_999:
        return f"{value:.2e}"
    else:
        return f"{value:.2f}"


class HistogramLUTTool(Graphic):
    def __init__(
            self,
            histogram: tuple[np.ndarray, np.ndarray],
            images: Sequence[ImageGraphic | ImageVolumeGraphic] | None = None,
            **kwargs,
    ):
        super().__init__(**kwargs)

        if len(histogram) != 2:
            raise TypeError

        self._block_reentrance = False
        self._images = list()

        self._bin_centers_flanked = np.zeros(120, dtype=np.float64)
        self._freq_flanked = np.zeros(120, dtype=np.float32)

        # 100 points for the histogram, 10 points on each side for the flank
        line_data = np.column_stack(
            [np.zeros(120, dtype=np.float32), np.arange(0, 120)]
        )

        self._line = LineGraphic(line_data, colors=(0.8, 0.8, 0.8), alpha_mode="solid", offset=(1, 0, 0))
        self._line.world_object.local.scale_x = -1

        self._selector = LinearRegionSelector(
            selection=(10, 110),
            limits=(0, 119),
            size=1.5,
            center=0.5,  # frequency data are normalized between 0-1
            axis="y",
            parent=self._line,
        )

        self._selector.add_event_handler(self._selector_event_handler, "selection")

        self._colorbar = ImageGraphic(
            data=np.zeros([120, 2]),
            interpolation="linear",
            offset=(1.5, 0, 0)
        )

        self._colorbar.world_object.local.scale_x = 0.15
        self._colorbar.add_event_handler(self._open_cmap_picker, "click")

        self._ruler = pygfx.Ruler(
            end_pos=(0, 119, 0),
            alpha_mode="solid",
            render_queue=RenderQueue.axes,
            tick_side="right",
            tick_marker="tick_right",
            tick_format=self._ruler_tick_map,
            min_tick_distance=10,
        )
        self._ruler.local.x = 1.75

        # TODO: need to auto-scale using the text so it appears nicely, will do later
        self._ruler.visible = False

        self._text_vmin = TextGraphic(
            text="",
            font_size=16,
            anchor="top-left",
            outline_color="black",
            outline_thickness=0.5,
            alpha_mode="solid",
        )
        # need to make sure text object doesn't conflict with selector tool
        self._text_vmin.world_object.material.pick_write = False

        self._text_vmax = TextGraphic(
            text="",
            font_size=16,
            anchor="bottom-left",
            outline_color="black",
            outline_thickness=0.5,
            alpha_mode="solid",
        )
        self._text_vmax.world_object.material.pick_write = False

        wo = pygfx.Group()
        wo.add(
            self._line.world_object,
            self._selector.world_object,
            self._colorbar.world_object,
            self._ruler,
            self._text_vmin.world_object,
            self._text_vmax.world_object
        )
        self._set_world_object(wo)

        self._children = [self._line, self._selector, self._colorbar, self._text_vmin, self._text_vmax]

        # set histogram
        self.histogram = histogram

        # set the images
        self.images = images

    def _fpl_add_plot_area_hook(self, plot_area):
        self._plot_area = plot_area
        for child in self._children:
            child._fpl_add_plot_area_hook(plot_area)

        if hasattr(self._plot_area, "size"):
            # if it's in a dock area
            self._plot_area.size = 80

        self._plot_area.controller.enabled = False
        self._plot_area.auto_scale(maintain_aspect=False)
        self._ruler.update(plot_area.camera, plot_area.canvas.get_logical_size())

    def _ruler_tick_map(self, bin_index, *args):
        return f"{self._bin_centers_flanked[int(bin_index)]:.2f}"

    @property
    def histogram(self) -> tuple[np.ndarray, np.ndarray]:
        """histogram [frequency, bin_centers]. Frequency is flanked by 10 zeros on both sides"""
        return self._freq_flanked, self._bin_centers_flanked

    @histogram.setter
    def histogram(self, histogram: tuple[np.ndarray, np.ndarray], limits: tuple[int, int] = None):
        freq, edges = histogram

        freq = (freq / freq.max())

        bin_centers = 0.5 * (edges[1:] + edges[:-1])

        step = bin_centers[1] - bin_centers[0]

        under_flank = np.linspace(bin_centers[0] - step * 10, bin_centers[0] - step, 10)
        over_flank = np.linspace(bin_centers[-1] + step, bin_centers[-1] + step * 10, 10)
        self._bin_centers_flanked[:] = np.concatenate([under_flank, bin_centers, over_flank])

        self._freq_flanked[10:110] = freq

        self._line.data[:, 0] = self._freq_flanked
        self._colorbar.data = np.column_stack([self._bin_centers_flanked, self._bin_centers_flanked])

        # self.vmin, self.vmax = bin_centers[0], bin_centers[-1]

        if hasattr(self, "plot_area"):
            self._ruler.update(self._plot_area.camera, self._plot_area.canvas.get_logical_size())

    @property
    def images(self) -> tuple[ImageGraphic | ImageVolumeGraphic, ...] | None:
        return tuple(self._images)

    @images.setter
    def images(self, new_images: tuple[ImageGraphic | ImageVolumeGraphic] | None):
        self._disconnect_images()
        self._images.clear()

        if new_images is None:
            return

        if isinstance(new_images, (ImageGraphic, ImageVolumeGraphic)):
            new_images = [new_images]

        if not all([isinstance(image, (ImageGraphic, ImageVolumeGraphic)) for image in new_images]):
            raise TypeError

        for image in new_images:
            if image.cmap is not None:
                self._colorbar.visible = True
                break
        else:
            self._colorbar.visible = False

        self._images = new_images

        # reset vmin, vmax using first image
        self.vmin = self._images[0].vmin
        self.vmax = self._images[0].vmax

        if self._images[0].cmap is not None:
            self._colorbar.cmap = self._images[0].cmap

        # connect event handlers
        for image in self._images:
            image.add_event_handler(self._image_event_handler, "vmin", "vmax")
            image.add_event_handler(self._disconnect_images, "deleted")
            if image.cmap is not None:
                image.add_event_handler(self._image_event_handler, "vmin", "vmax", "cmap")

    def _disconnect_images(self, *args):
        for image in self._images:
            for ev, handlers in image.event_handlers:
                if self._image_event_handler in handlers:
                    image.remove_event_handler(self._image_event_handler, ev)

    def _image_event_handler(self, ev):
        new_value = ev.info["value"]
        setattr(self, ev.type, new_value)

    @property
    def cmap(self) -> str:
        return self._colorbar.cmap

    @cmap.setter
    def cmap(self, name: str):
        if self._block_reentrance:
            return

        if name is None:
            return

        self._block_reentrance = True
        try:
            self._colorbar.cmap = name

            with pause_events(*self._images, event_handlers=[self._image_event_handler]):
                for image in self._images:
                    image.cmap = name
        except Exception as exc:
            # raise original exception
            raise exc  # vmax setter has raised. The lines above below are probably more relevant!
        finally:
            # set_value has finished executing, now allow future executions
            self._block_reentrance = False

    @property
    def vmin(self) -> float:
        # no offset or rotation so we can directly use the world space selection value
        index = int(self._selector.selection[0])
        return self._bin_centers_flanked[index]

    @vmin.setter
    def vmin(self, value: float):
        if self._block_reentrance:
            return
        self._block_reentrance = True
        try:
            index_min = np.searchsorted(self._bin_centers_flanked, value)
            with pause_events(self._selector, *self._images, event_handlers=[self._selector_event_handler, self._image_event_handler]):
                self._selector.selection = (index_min, self._selector.selection[1])

                self._colorbar.vmin = value

                self._text_vmin.text = _format_value(value)
                self._text_vmin.offset = (-0.45, self._selector.selection[0], 0)

                for image in self._images:
                    image.vmin = value

        except Exception as exc:
            # raise original exception
            raise exc  # vmax setter has raised. The lines above below are probably more relevant!
        finally:
            # set_value has finished executing, now allow future executions
            self._block_reentrance = False

    @property
    def vmax(self) -> float:
        # no offset or rotation so we can directly use the world space selection value
        index = int(self._selector.selection[1])
        return self._bin_centers_flanked[index]

    @vmax.setter
    def vmax(self, value: float):
        if self._block_reentrance:
            return

        self._block_reentrance = True
        try:
            index_max = np.searchsorted(self._bin_centers_flanked, value)
            with pause_events(self._selector, *self._images, event_handlers=[self._selector_event_handler, self._image_event_handler]):
                self._selector.selection = (self._selector.selection[0], index_max)

                self._colorbar.vmax = value

                self._text_vmax.text = _format_value(value)
                self._text_vmax.offset = (-0.45, self._selector.selection[1], 0)

                for image in self._images:
                    image.vmax = value

        except Exception as exc:
            # raise original exception
            raise exc  # vmax setter has raised. The lines above below are probably more relevant!
        finally:
            # set_value has finished executing, now allow future executions
            self._block_reentrance = False

    def _selector_event_handler(self, ev: GraphicFeatureEvent):
        selection = ev.info["value"]
        index_min = int(selection[0])
        vmin = self._bin_centers_flanked[index_min]

        index_max = int(selection[1])
        vmax = self._bin_centers_flanked[index_max]

        match ev.info["change"]:
            case "min":
                self.vmin = vmin
            case "max":
                self.vmax = vmax
            case _:
                self.vmin, self.vmax = vmin, vmax

    def _open_cmap_picker(self, ev):
        # check if right click
        if ev.button != 2:
            return

        pos = ev.x, ev.y

        self._plot_area.get_figure().open_popup("colormap-picker", pos, lut_tool=self)

    def _fpl_prepare_del(self):
        self._disconnect_images()
        self._images.clear()

        for i in range(len(self._children)):
            g = self._children.pop(0)
            g._fpl_prepare_del()
            del g
