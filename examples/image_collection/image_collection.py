"""
Image Collection
================

Position a collection of images individually using per-image ``offsets``.
"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'screenshot'

import numpy as np
import fastplotlib as fpl

rng = np.random.default_rng(0)

# a collection of random 100 x 100 images
images = [rng.random((100, 100), dtype=np.float32) for _ in range(5)]

figure = fpl.Figure(size=(700, 560))

# stagger the images diagonally with one (x, y, z) offset per image
offsets = np.array([[i * 60, -i * 60, 0] for i in range(len(images))])

figure[0, 0].add_image_collection(images, offsets=offsets, cmap="viridis")

figure.show()

# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
