"""
Specify IDs with integers
=========================

Specify controllers to sync subplots using integer IDs
"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'screenshot'

import numpy as np
import fastplotlib as fpl


xs = np.linspace(0, 2 * np.pi, 100)
sine = np.sin(xs)
cosine = np.cos(xs)

# controller IDs
# one controller is created for each unique ID
# if the IDs are the same, those subplots will be synced
ids = [
    [0, 1],
    [2, 0],
]

figure = fpl.Figure(
    shape=(2, 2),
    controller_ids=ids,
    size=(700, 560),
)

for subplot, controller_id in zip(figure, np.asarray(ids).ravel()):
    subplot.title = f"contr. id: {controller_id}"

figure[0, 0].add_line(np.column_stack([xs, sine]))

figure[0, 1].add_line(np.random.rand(100))
figure[1, 0].add_line(np.random.rand(100))

figure[1, 1].add_line(np.column_stack([xs, cosine]))

figure.show(maintain_aspect=False)


# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
