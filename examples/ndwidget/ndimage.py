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
data2 = np.random.rand(1000, 30, 128, 128)

# must define a reference range for each dim
ref = {
    "time": (0, 1000, 1),
    "depth": (0, 30, 1),
}


ndw = fpl.NDWidget(
    ref_ranges=ref,
    size=(700, 560)
)
ndw2 = fpl.NDWidget(
    ref_ranges=ref,
    ref_index=ndw.indices, # can create another NDWidget that shared the reference index! So multiple windows are possible
    size=(700, 560)
)

ndi = ndw[0, 0].add_nd_image(
    data,
    ("time", "depth", "m", "n"),  # specify all dim names
    ("m", "n"),  # specify spatial dims IN ORDER, rest are auto slider dims
    name="4d-image",
)

ndi2 = ndw2[0, 0].add_nd_image(
    data2,
    ("time", "depth", "m", "n"),  # specify all dim names
    ("m", "n"),  # specify spatial dims IN ORDER, rest are auto slider dims
    name="4d-image",
)

# change spatial dims on the fly
# ndi.spatial_dims = ("depth", "m", "n")

ndw.show()
ndw2.show()
fpl.loop.run()
