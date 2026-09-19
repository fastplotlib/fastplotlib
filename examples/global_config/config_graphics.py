"""
Graphics Config
===============

Configuration values are used for any argument that is not explicitly passed.
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

import imageio.v3 as iio
import numpy as np
import fastplotlib as fpl

fpl.LineGraphic.config.init.colors = "magenta"
fpl.LineGraphic.config.init.thickness = 4

fpl.ScatterGraphic.config.init.markers = "^"
fpl.ScatterGraphic.config.init.sizes = 20
fpl.ScatterGraphic.config.init.colors = "r"

fpl.VectorsGraphic.config.init.color = "cyan"

fpl.ImageGraphic.config.init.cmap = "viridis"

xs = np.linspace(0, 4 * np.pi, 100)
ys = np.sin(xs)
line_data = np.column_stack([xs, ys])
cosine_data = np.column_stack([xs, np.cos(xs)])

# 5 sine waves to stack
stack_data = np.stack([line_data] * 5)

# uniform x, y positions for the vectors and their directions
x, y = np.meshgrid(np.arange(0, 2 * np.pi, 0.4), np.arange(0, 2 * np.pi, 0.4))
positions = np.column_stack([x.ravel(), y.ravel()])
directions = np.column_stack([np.cos(x).ravel(), np.sin(y).ravel()])

image_data = iio.imread("imageio:camera.png")

figure = fpl.Figure(shape=(2, 2), size=(700, 800))

figure[0, 0].add_line(cosine_data, offset=(0, -3, 0))

# any explicitly provided arg , e.g.`colors`, overrides the config value
figure[0, 0].add_scatter(line_data[::5], colors="green")

# a stack creates lines, so they use the LineGraphic config too
figure[0, 1].add_line_stack(stack_data)

figure[1, 0].add_vectors(positions=positions, directions=directions)

figure[1, 1].add_image(image_data)

figure.show()


# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
