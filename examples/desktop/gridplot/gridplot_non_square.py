"""
GridPlot Simple
============
Example showing simple 2x2 GridPlot with Standard images from imageio.
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

import fastplotlib as fpl
import imageio.v3 as iio

fig = fpl.Figure(shape=(2, 2), controller_ids="sync")

im = iio.imread("imageio:clock.png")
im2 = iio.imread("imageio:astronaut.png")
im3 = iio.imread("imageio:coffee.png")

fig[0, 0].add_image(data=im)
fig[0, 1].add_image(data=im2)
fig[1, 0].add_image(data=im3)

fig.show()

# set canvas variable for sphinx_gallery to properly generate examples
canvas = fig.canvas

fig.canvas.set_logical_size(800, 800)

for subplot in fig:
    subplot.auto_scale()

if __name__ == "__main__":
    print(__doc__)
    fpl.run()
