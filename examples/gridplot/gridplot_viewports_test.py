"""
GridPlot test viewport rects
============================

Test figure to test that viewport rects are positioned correctly
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'hidden'

import fastplotlib as fpl
import numpy as np


figure = fpl.Figure(
    shape=(2, 3),
    size=(700, 560),
    names=list(map(str, range(6)))
)

np.random.seed(0)
a = np.random.rand(6, 10, 10)

for data, subplot in zip(a, figure):
    subplot.add_image(data)
    subplot.docks["left"].size = 20
    subplot.docks["right"].size = 30
    subplot.docks["bottom"].size = 40

figure.show()


# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# please see our docs for using fastplotlib interactively in ipython and jupyter
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
