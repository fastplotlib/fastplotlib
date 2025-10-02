"""
Grid layout Simple
==================

Example showing simple 2x2 grid layout with standard images from imageio.
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

import fastplotlib as fpl
import imageio.v3 as iio
import numpy as np

figure = fpl.Figure(shape=(2, 2), size=(700, 560))

im1 = iio.imread("imageio:clock.png")
im2 = iio.imread("imageio:astronaut.png")[:500,:300]
im3 = iio.imread("imageio:coffee.png")
im4 = iio.imread("imageio:hubble_deep_field.png")

xs = np.linspace(-10, 10, 100)
a = 0.5
ys = np.sinc(xs) * 3 + 8
sinc_data = np.column_stack([xs, ys])

i1=figure[0, 0].add_image(data=im1)
i2=figure[0, 0].add_image(data=im2)
figure[1, 0].add_image(data=im3)
x = figure[1, 1].add_line(sinc_data,  thickness=12, cmap="autumn")
y = figure[1, 1].add_line(sinc_data,  thickness=2, cmap="jet")

figure.show()


r = figure[0,1].scene.children[2].children[0]
i = figure[0,1].graphics[0].world_object.children[0]


# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
