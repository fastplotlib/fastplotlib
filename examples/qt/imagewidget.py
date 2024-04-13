"""
Use ImageWidget to display one or multiple image sequences
"""
import numpy as np
from PyQt6 import QtWidgets
import fastplotlib as fpl
import imageio.v3 as iio


images = np.random.rand(100, 512, 512)

# fastplotlib and wgpu will auto-detect if Qt is imported and then use the Qt canvas
iw = fpl.ImageWidget(images)
iw.show()
iw.widget.resize(800, 800)

# another image widget with multiple images
images_list = [np.random.rand(100, 512, 512) for i in range(9)]

iw_mult = fpl.ImageWidget(
    images_list,
    cmap="viridis"
)
iw_mult.show()
iw_mult.widget.resize(800, 800)

# image widget with rgb data
rgb_video = iio.imread("imageio:cockatoo.mp4")
iw_rgb = fpl.ImageWidget(rgb_video, rgb=[True])
iw_rgb.show()

fpl.run()
