"""
Wide Heatmap
============
Wide example
"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'hidden'

import fastplotlib as fpl
import numpy as np


figure = fpl.Figure(size=(700, 560))

xs = np.linspace(0, 1_000, 20_000, dtype=np.float32)

sine = np.sin(np.sqrt(xs))

data = np.vstack([sine * i for i in range(10_000)])

# plot the image data
img = figure[0, 0].add_image(data=data, name="heatmap")

figure.show()


if __name__ == "__main__":
    print(__doc__)
    fpl.run()
