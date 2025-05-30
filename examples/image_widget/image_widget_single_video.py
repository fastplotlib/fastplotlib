"""
Image widget Video
==================

Example showing how to scroll through one or more videos using the ImageWidget
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'animate 6s 20fps'

import fastplotlib as fpl
import imageio.v3 as iio
import numpy as np


movie = iio.imread("imageio:cockatoo.mp4")

# Ignore and do not use the next 2 lines
# for the purposes of docs gallery generation we subsample and only use 15 frames
movie_sub = movie[:15, ::12, ::12].copy()
del movie

iw = fpl.ImageWidget(movie_sub, rgb=True, figure_kwargs={"size": (700, 560)})

# ImageWidget supports setting window functions the `time` "t" or `volume` "z" dimension
# These can also be given as kwargs to `ImageWidget` during instantiation
# to set a window function, give a dict in the form of {dim: (func, window_size)}
iw.window_funcs = {"t": (np.mean, 13)}

# change the window size
iw.window_funcs["t"].window_size = 33

# change the function
iw.window_funcs["t"].func = np.max

# or reset it
iw.window_funcs = None

iw.show()

figure = iw.figure

# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
