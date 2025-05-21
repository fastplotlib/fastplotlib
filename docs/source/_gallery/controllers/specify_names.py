"""
Specify IDs with subplot names
==============================

Provide a list of tuples where each tuple has subplot names. The same controller will be used for the subplots
indicated by each of these tuples
"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'screenshot'

import numpy as np
import fastplotlib as fpl


xs = np.linspace(0, 2 * np.pi, 100)
ys = np.sin(xs)

# create some subplots names
names = ["subplot_0", "subplot_1", "subplot_2", "subplot_3", "subplot_4", "subplot_5"]

# list of tuples of subplot names
# subplots within each tuple will use the same controller.
ids = [
    ("subplot_0", "subplot_3"),
    ("subplot_1", "subplot_2", "subplot_4"),
]


figure = fpl.Figure(
    shape=(2, 3),
    controller_ids=ids,
    names=names,
    size=(700, 560),
)

for subplot in figure:
    subplot.add_line(np.column_stack([xs, ys + np.random.normal(scale=0.1, size=100)]))

figure.show(maintain_aspect=False)


# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# please see our docs for using fastplotlib interactively in ipython and jupyter
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
