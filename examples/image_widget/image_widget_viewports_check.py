"""
ImageWidget test viewport rects
===============================

Test Figure to test that viewport rects are positioned correctly in an image widget
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'hidden'

import fastplotlib as fpl
import numpy as np

np.random.seed(0)
a = np.random.rand(6, 15, 10, 10)

iw = fpl.ImageWidget(
    data=[img for img in a],
    names=list(map(str, range(6))),
    figure_kwargs={"size": (700, 560)},
)

for subplot in iw.figure:
    subplot.docks["left"].size = 10
    subplot.docks["bottom"].size = 40

iw.show()

figure = iw.figure

# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
