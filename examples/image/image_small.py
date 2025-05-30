"""
Small Image
===========

Test image to verify dims
"""

import numpy as np

# test_example = true
# sphinx_gallery_pygfx_docs = 'hidden'

import fastplotlib as fpl

figure = fpl.Figure(size=(700, 560))

data = np.array(
    [[0, 1, 2],
     [3, 4, 5]]
)
image_graphic = figure[0, 0].add_image(data)

figure.show()

# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
