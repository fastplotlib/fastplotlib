"""
Tooltips
========

Show tooltips on all graphics
"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'screenshot'

import numpy as np
import imageio.v3 as iio
import fastplotlib as fpl


# get some data
scatter_data = np.random.rand(1_000, 3)

xs = np.linspace(0, 2 * np.pi, 100)
ys = np.sin(xs)

gray = iio.imread("imageio:camera.png")
rgb = iio.imread("imageio:astronaut.png")

# create a figure
figure = fpl.Figure(
    cameras=["3d", "2d", "2d", "2d"],
    controller_types=["orbit", "panzoom", "panzoom", "panzoom"],
    size=(700, 560),
    shape=(2, 2),
    show_tooltips=True,  # tooltip will display data value info for all graphics
)

# create graphics
scatter = figure[0, 0].add_scatter(scatter_data, sizes=3, colors="r")
line = figure[0, 1].add_line(np.column_stack([xs, ys]))
image = figure[1, 0].add_image(gray)
image_rgb = figure[1, 1].add_image(rgb)


figure.show()

# to hide tooltips for all graphics in an existing Figure
# figure.show_tooltips = False

# to show tooltips for all graphics in an existing Figure
# figure.show_tooltips = True


# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
