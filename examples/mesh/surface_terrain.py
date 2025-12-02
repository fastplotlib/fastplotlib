"""
Elevation map of the earth
==========================

Surface graphic showing elevation map of the earth
"""

# run_example = false
# sphinx_gallery_pygfx_docs = 'code'

import imageio.v3 as iio
import fastplotlib as fpl
import numpy as np

# grayscale image of the earth where the pixel value indicates elevation
elevation = iio.imread("https://neo.gsfc.nasa.gov/archive/bluemarble/bmng/topography/srtm_ramp2.world.5400x2700.jpg").astype(np.float32)
elevation /= 2

figure = fpl.Figure(size=(700, 560), cameras="3d", controller_types="orbit")

mesh = figure[0, 0].add_surface(elevation, cmap="terrain")
mesh.world_object.local.scale_y = -1


figure[0, 0].axes.grids.xy.visible = True
figure[0, 0].camera.show_object(mesh.world_object, (-4, 2, -1), up=(0, 0, 1))
figure.show()

figure[0, 0].camera.zoom = 2.5


# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
