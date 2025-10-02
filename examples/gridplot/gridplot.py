"""
Grid layout Simple
==================

Example showing simple 2x2 grid layout with standard images from imageio.
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

import fastplotlib as fpl
import imageio.v3 as iio

figure = fpl.Figure(shape=(2, 2), size=(700, 560))

im = iio.imread("imageio:clock.png")
im2 = iio.imread("imageio:astronaut.png")
im3 = iio.imread("imageio:coffee.png")
im4 = iio.imread("imageio:hubble_deep_field.png")

figure[0, 0].add_image(data=im)
figure[0, 1].add_image(data=im2)
figure[1, 0].add_image(data=im3)
figure[1, 1].add_image(data=im4)

figure.show()


# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()