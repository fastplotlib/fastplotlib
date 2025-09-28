"""
Volume Mip mode
===============

View a volume using MIP rendering.
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

import numpy as np
import fastplotlib as fpl
import imageio.v3 as iio

voldata = iio.imread("imageio:stent.npz").astype(np.float32)

figure = fpl.Figure(cameras="3d", controller_types="orbit", size=(700, 560))

figure[0, 0].add_image_volume(voldata, mode="mip", alpha_mode="add")

figure.show()


# load a pre-saved camera state
state = {
    "position": np.array([-120, 90, 330]),
    "rotation": np.array([-0.07280538, -0.41100206, -0.03295049, 0.90812496]),
    "scale": np.array([1.0, 1.0, 1.0]),
    "reference_up": np.array([0.0, 1.0, 0.0]),
    "fov": 50.0,
    "width": 128.0,
    "height": 128.0,
    "depth": 313,
    "zoom": 0.75,
    "maintain_aspect": True,
    "depth_range": None,
}


figure[0, 0].camera.set_state(state)


# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
