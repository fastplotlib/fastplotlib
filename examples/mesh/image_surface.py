"""
Image surface
=============

Example showing an image as a surface.
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

import imageio.v3 as iio
import fastplotlib as fpl
import scipy.ndimage

im = iio.imread("imageio:astronaut.png")

figure = fpl.Figure(size=(700, 560), cameras="3d", controller_types="orbit")


# Create the height map from the image
z = im.mean(axis=2)
z = scipy.ndimage.gaussian_filter(z, 5)  # 2nd arg is sigma

mesh = figure[0, 0].add_surface(z, colors="magenta", cmap=im)
mesh.world_object.local.scale_y = -1


figure[0, 0].axes.grids.xy.visible = True
figure[0, 0].camera.show_object(mesh.world_object, (1, 2, -1), up=(0, 0, 1))
figure.show()


# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
