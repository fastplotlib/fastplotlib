"""
Small Image
===========

Test image to verify dims
"""

import numpy as np

# test_example = true
# sphinx_gallery_pygfx_docs = 'hidden'

import fastplotlib as fpl

figure = fpl.Figure()

data = np.array(
    [[0, 1, 2],
     [3, 4, 5]]
)
image_graphic = figure[0, 0].add_image(data)

figure.show()

figure.canvas.set_logical_size(700, 560)

figure[0, 0].auto_scale()

# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# please see our docs for using fastplotlib interactively in ipython and jupyter
if __name__ == "__main__":
    print(__doc__)
    fpl.run()
