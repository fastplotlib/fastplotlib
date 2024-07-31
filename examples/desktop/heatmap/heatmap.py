"""
Simple Heatmap
==============
Example showing how to plot a heatmap
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

import fastplotlib as fpl
import numpy as np

figure = fpl.Figure(size=(700, 560))

xs = np.linspace(0, 1_000, 9_000, dtype=np.float32)

sine = np.sin(np.sqrt(xs))

data = np.vstack([sine * i for i in range(15_000)])

# plot the image data
img = figure[0, 0].add_image(data=data, name="heatmap")
del data

figure.show()


# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# please see our docs for using fastplotlib interactively in ipython and jupyter
if __name__ == "__main__":
    print(__doc__)
    fpl.run()
