"""
Image reshaping
===============

An example that shows replacement of the image data with new data of a different shape. Under the hood, this creates a
new buffer and a new array of Textures on the GPU that replace the older Textures. Creating a new buffer and textures
has a performance cost, so you should do this only if you need to or if the performance drawback is not a concern for
your use case.

Note that the vmin-vmax is reset when you replace the buffers.
"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'animate'


import numpy as np
import fastplotlib as fpl

# create some data, diagonal sinusoidal bands
xs = np.linspace(0, 2300, 2300, dtype=np.float16)
full_data = np.vstack([np.cos(np.sqrt(xs + (np.pi / 2) * i)) * i for i in range(2_300)])

fig = fpl.Figure()

image = fig[0, 0].add_image(full_data)

fig.show()

i, j = 1, 1


def update():
    global i, j
    row = np.abs(np.sin(i)) * 2300
    col = np.abs(np.cos(i)) * 2300
    image.data = full_data[: int(row), : int(col)]

    i += 0.01
    j += 0.01


fig.add_animations(update)

# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
