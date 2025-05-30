"""
Heatmap or large arrays
=======================
Example showing how ImageGraphics can be useful for viewing large arrays, these can be in the order of 10^4 x 10^4.
The performance and limitations will depend on your hardware.
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

import fastplotlib as fpl
import numpy as np


figure = fpl.Figure(size=(700, 560))

xs = np.linspace(0, 1000, 20_000, dtype=np.float16)

sine = np.sin(np.sqrt(xs))

data = np.vstack([sine * i for i in range(20_000)])

# plot the image data
img = figure[0, 0].add_image(data=data, name="heatmap")
del data

figure.show()

# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
