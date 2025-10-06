"""
Volume modes
============

View a volume using different rendering modes.
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

import numpy as np
import fastplotlib as fpl
from fastplotlib.ui import EdgeWindow
from fastplotlib.graphics.features import VOLUME_RENDER_MODES
import imageio.v3 as iio
from imgui_bundle import imgui

voldata = iio.imread("imageio:stent.npz").astype(np.float32)

figure = fpl.Figure(
    cameras="3d",
    controller_types="orbit",
    size=(700, 560)
)

figure[0, 0].add_image_volume(voldata, name="vol-img")

# add an hlut tool
hlut = fpl.HistogramLUTTool(voldata, figure[0, 0]["vol-img"])

figure[0, 0].docks["right"].size = 80
figure[0, 0].docks["right"].controller.enabled = False
figure[0, 0].docks["right"].add_graphic(hlut)
figure[0, 0].docks["right"].auto_scale(maintain_aspect=False)


class GUI(EdgeWindow):
    def __init__(self, figure, title="Render options", location="right", size=300):
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

        if self.graphic.mode == "slice":
            imgui.text("Select plane defined by:\nax + by + cz + d = 0")
            _, a = imgui.slider_float("a", v=self.graphic.plane[0], v_min=-1, v_max=1.0)
            _, b = imgui.slider_float("b", v=self.graphic.plane[1], v_min=-1, v_max=1.0)
            _, c = imgui.slider_float("c", v=self.graphic.plane[2], v_min=-1, v_max=1.0)

            largest_dim = max(self.graphic.data.value.shape)
            _, d = imgui.slider_float("d", v=self.graphic.plane[3], v_min=0, v_max=largest_dim * 2)

            self.graphic.plane = (a, b, c, d)

gui = GUI(figure=figure)
figure.add_gui(gui)

figure.show()


# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
