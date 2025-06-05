"""
Volume Mip mode
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

fig = fpl.Figure(cameras="3d", controller_types="orbit", size=(700, 560))

fig[0, 0].add_image_volume(voldata, mode="iso")

fig.show()

# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
