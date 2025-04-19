"""
Volume Ray mode
===============

View a volume, uses the fly controller by default so you can fly around the scene using WASD keys and the mouse:
https://docs.pygfx.org/stable/_autosummary/controllers/pygfx.controllers.FlyController.html#pygfx.controllers.FlyController
"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'screenshot'

import numpy as np
import fastplotlib as fpl
import imageio.v3 as iio

voldata = iio.imread("imageio:stent.npz").astype(np.float32)

fig = fpl.Figure(cameras="3d", size=(700, 560))

fig[0, 0].add_image_volume(voldata)

fig.show()

fpl.loop.run()
