"""
Image widget Video
==================

Example showing how to scroll through one or more videos using the ImageWidget
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

import fastplotlib as fpl
import imageio.v3 as iio
import numpy as np


movie = iio.imread("imageio:cockatoo.mp4")

iw_movie = fpl.ImageWidget(
    data=movie,
    rgb=[True]
)

# ImageWidget supports setting window functions the `time` "t" or `volume` "z" dimension
# These can also be given as kwargs to `ImageWidget` during instantiation
# to set a window function, give a dict in the form of {dim: (func, window_size)}
iw_movie.window_funcs = {"t": (np.mean, 13)}

# change the winow size
iw_movie.window_funcs["t"].window_size = 33

# change the function
iw_movie.window_funcs["t"].func = np.max

# or reset it
iw_movie.window_funcs = None

figure = iw_movie.figure

# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# please see our docs for using fastplotlib interactively in ipython and jupyter
if __name__ == "__main__":
    print(__doc__)
    fpl.run()
