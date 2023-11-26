"""
GridPlot Simple
============
Example showing simple 2x2 GridPlot with Standard images from imageio.
"""

# test_example = true

import fastplotlib as fpl
import imageio.v3 as iio


plot = fpl.GridPlot(shape=(2, 2), controller_ids="sync")
# to force a specific framework such as glfw:
# plot = fpl.GridPlot(canvas="glfw")

im = iio.imread("imageio:clock.png")
im2 = iio.imread("imageio:astronaut.png")
im3 = iio.imread("imageio:coffee.png")

plot[0, 0].add_image(data=im)
plot[0, 1].add_image(data=im2)
plot[1, 0].add_image(data=im3)

plot.show()

plot.canvas.set_logical_size(800, 800)

for subplot in plot:
    subplot.auto_scale()

if __name__ == "__main__":
    print(__doc__)
    fpl.run()
