"""
Volume non-orthogonal slicing
=============================

Perform non-orthogonal slicing of image volumes.

For an example with UI sliders see the "Volume modes" example.
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

import numpy as np
import fastplotlib as fpl
import imageio.v3 as iio


voldata = iio.imread("imageio:stent.npz").astype(np.float32)

fig = fpl.Figure(
    cameras="3d",
    controller_types="orbit",
    size=(700, 560)
)

vol = fig[0, 0].add_image_volume(voldata, mode="slice")

# a plane is defined by ax + by + cz + d = 0
# the plane property sets (a, b, c, d)
vol.plane = (0, 0.5, 0.5, -70)

# just a pre-saved camera state to view the plot area
state = {
    "position": np.array([-160.0,  105.0,  205.0]),
    "rotation": np.array([-0.1, -0.6, -0.07,  0.8]),
    "scale": np.array([1., 1., 1.]),
    "reference_up": np.array([0., 1., 0.]),
    "fov": 50.0,
    "width": 128.0,
    "height": 128.0,
    "depth": 315,
    "zoom": 0.75,
    "maintain_aspect": True,
    "depth_range": None
}

fig.show()

fig[0, 0].camera.set_state(state)

# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
