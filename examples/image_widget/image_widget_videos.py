"""
Image widget videos side by side
================================

Example showing how to scroll through one or more videos using the ImageWidget
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'animate 6s 20fps'

import fastplotlib as fpl
import imageio.v3 as iio
import numpy as np


# load the standard cockatoo video
cockatoo = iio.imread("imageio:cockatoo.mp4")

# Ignore and do not use the next 2 lines
# for the purposes of docs gallery generation we subsample and only use 15 frames
cockatoo_sub = cockatoo[:15, ::12, ::12].copy()
del cockatoo

# make a random grayscale video, shape is [t, rows, cols]
np.random.seed(0)
random_data = np.random.rand(*cockatoo_sub.shape[:-1])

iw = fpl.ImageWidget(
    [random_data, cockatoo_sub],
    rgb=[False, True],
    figure_shape=(2, 1),  # 2 rows, 1 column
    figure_kwargs={"size": (700, 940)}
)

iw.show()

figure = iw.figure

# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
