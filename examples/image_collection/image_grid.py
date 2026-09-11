"""
Image Grid
==========

Arrange a collection of images in a grid using ``shape`` and ``separation``.
"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'screenshot'

import numpy as np
import fastplotlib as fpl

rng = np.random.default_rng(0)

# a collection of random 100 x 100 images
images = [rng.random((100, 100), dtype=np.float32) for _ in range(6)]

figure = fpl.Figure(size=(700, 560))

# lay the images out in a 2 x 3 grid with a gap between rows and columns
figure[0, 0].add_image_grid(images, shape=(2, 3), separation=(10, 10), cmap="plasma")

figure.show()

# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
