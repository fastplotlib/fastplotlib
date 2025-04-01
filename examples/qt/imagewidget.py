"""
ImageWidget as QtWidget
=======================

This example opens multiple windows to show multiple ImageWidgets.
"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'code'

import numpy as np
import fastplotlib as fpl
import imageio.v3 as iio


images = np.random.rand(100, 512, 512)

# fastplotlib and wgpu will auto-detect if Qt is imported and then use the Qt canvas
iw = fpl.ImageWidget(images)
widget = iw.show()
widget.resize(800, 800)

# another image widget with multiple images
images_list = [np.random.rand(100, 512, 512) for i in range(4)]

iw_mult = fpl.ImageWidget(images_list, cmap="viridis")
widget_multi = iw_mult.show()
widget_multi.resize(800, 800)

# image widget with rgb data
rgb_video = iio.imread("imageio:cockatoo.mp4")
iw_rgb = fpl.ImageWidget(rgb_video, rgb=[True], figure_kwargs={"size": (800, 500)})
iw_rgb.show()

fpl.loop.run()

# You can also use Qt interactively/in a non-blocking manner in notebooks and ipython
# by using %gui qt and NOT calling `fpl.loop.run()`, see the user guide for more details
