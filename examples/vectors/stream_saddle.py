"""
Saddle Stream Plot
==================

Streamlines of a linear field with a saddle at the origin.

"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'screenshot'

import numpy as np
import fastplotlib as fpl

figure = fpl.Figure(size=(700, 700))

x, y = np.meshgrid(np.linspace(-3, 3, 24), np.linspace(-3, 3, 24))

# the field {y, x + y} from the Mathematica StreamPlot reference page
u = y
v = x + y

positions = np.column_stack([x.ravel(), y.ravel()])
directions = np.column_stack([u.ravel(), v.ravel()])

stream = figure[0, 0].add_stream(
    positions=positions,
    directions=directions,
    cmap="magma",
)

figure.show()

# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
