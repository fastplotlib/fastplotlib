"""
Volume modes
============

View a volume using different rendering modes
"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'screenshot'

import numpy as np
import fastplotlib as fpl
from fastplotlib.ui import EdgeWindow
from fastplotlib.graphics.features import VOLUME_RENDER_MODES
import imageio.v3 as iio
from imgui_bundle import imgui

voldata = iio.imread("imageio:stent.npz").astype(np.float32)

fig = fpl.Figure(
    cameras="3d",
    controller_types="orbit",
    size=(700, 560)
)

fig[0, 0].add_image_volume(voldata, name="vol-img")


class GUI(EdgeWindow):
    def __init__(self, figure, title="Render options", location="right", size=250):
        super().__init__(figure, title=title, location=location, size=size)

        # reference to the graphic for convenience
        self.graphic: fpl.ImageVolumeGraphic = self._figure[0, 0]["vol-img"]

    def update(self):
        imgui.text("Switch render mode:")

        # add buttons to switch between modes
        for mode in VOLUME_RENDER_MODES.keys():
            if imgui.button(mode):
                self.graphic.mode = mode

        # add sliders to change iso rendering properties
        if self.graphic.mode == "iso":
            _, self.graphic.threshold = imgui.slider_float(
                "threshold", v=self.graphic.threshold, v_max=255, v_min=1,
            )
            _, self.graphic.step_size = imgui.slider_float(
                "step_size", v=self.graphic.step_size, v_max=10.0, v_min=0.1,
            )
            _, self.graphic.substep_size = imgui.slider_float(
                "substep_size", v=self.graphic.substep_size, v_max=10.0, v_min=0.1,
            )
            _, self.graphic.emissive = imgui.color_picker3("emissive color", col=self.graphic.emissive.rgb)

gui = GUI(figure=fig)
fig.add_gui(gui)

fig.show()

fpl.loop.run()
