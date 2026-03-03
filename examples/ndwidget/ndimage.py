"""
NDWidget image
==============

NDWidget image example
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

import numpy as np
import fastplotlib as fpl


data = np.random.rand(1000, 30, 64, 64)

# must define a reference range for each dim
ref = {
    "time": ("time", "s", 0, 1000, 1),
    "depth": ("depth", "um", 0, 30, 1),
}


ndw = fpl.NDWidget(ref_ranges=ref, size=(700, 560))
ndw.show()

ndi = ndw[0, 0].add_nd_image(
    data,
    ("time", "depth", "m", "n"),  # specify all dim names
    ("m", "n"),  # specify spatial dims IN ORDER, rest are auto slider dims
)

# change spatial dims on the fly
ndi.spatial_dims = ("depth", "m", "n")

fpl.loop.run()
