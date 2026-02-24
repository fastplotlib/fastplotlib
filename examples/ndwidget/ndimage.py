"""
NDWidget image
==============

NDWidget image example
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

import numpy as np
import fastplotlib as fpl


a = np.random.rand(30, 1000, 64, 64)


ndw = fpl.NDWidget(ref_ranges=[(0, 30, 1, "um"), (0, 1000, 1, "t")], size=(800, 800))
ndw.show()

ndi = ndw[0, 0].add_nd_image(a, index_mappings=(int, int))
# TODO: need to think about how to "auto ignore" reference range for a dim when switching between 2 & 3 dim images
# ndi.n_display_dims = 3

fpl.loop.run()
