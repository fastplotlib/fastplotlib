"""
GridPlot Simple
============
Example showing simple 2x2 GridPlot with Standard images from imageio.
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

import fastplotlib as fpl
import imageio.v3 as iio
from wgpu.gui.auto import WgpuCanvas

canvas = WgpuCanvas(size=(800, 800))


fig = fpl.Figure(shape=(2, 2), canvas=canvas)

im = iio.imread("imageio:clock.png")
im2 = iio.imread("imageio:astronaut.png")
im3 = iio.imread("imageio:coffee.png")
im4 = iio.imread("imageio:hubble_deep_field.png")

fig[0, 0].add_image(data=im)
fig[0, 1].add_image(data=im2)
fig[1, 0].add_image(data=im3)
fig[1, 1].add_image(data=im4)

#canvas = fig.canvas

fig.show()

#fig.canvas.set_logical_size(800, 800)

for subplot in fig:
    subplot.auto_scale()

if __name__ == "__main__":
    print(__doc__)
    fpl.run()
