"""
ImageWidget Simple
============

Example showing simple ImageWidget with pre-saved 512x512 random image.
"""

# test_example = true

from fastplotlib import ImageWidget
import numpy as np

from wgpu.gui.offscreen import WgpuCanvas
from pygfx import WgpuRenderer

canvas = WgpuCanvas()
renderer = WgpuRenderer(canvas)

a = np.random.rand(500, 512, 512)

data = np.load("../data/random3D.npy")

iw = ImageWidget(
    data=data,
    slider_dims=["t"],
    vmin_vmax_sliders=True,
    cmap="gnuplot2"
)

data = np.load("../data/random.npy")

iw.show()

iw["t"] = 250

iw.plot.center_scene()

img = np.asarray(iw.renderer.target.draw())

#np.save('../screenshots/iw_simple.npy', img)

if __name__ == "__main__":
    print(__doc__)
