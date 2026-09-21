"""
Simple Stream Plot
==================

Simple example with streamlines of a vector field. Similar to Mathematica StreamPlot.

"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'screenshot'

import numpy as np
import fastplotlib as fpl

figure = fpl.Figure(size=(700, 700))

# the vector field from the Mathematica StreamPlot reference page
x, y = np.meshgrid(np.linspace(-3, 3, 24), np.linspace(-3, 3, 24))

# u and v are the x and y components of the field
u = -1 - x**2 + y
v = 1 + x - y**2

# positions of each field sample as an [n_points, 2] array
positions = np.column_stack([x.ravel(), y.ravel()])
# field vector at each position as an [n_points, 2] array
directions = np.column_stack([u.ravel(), v.ravel()])

# a cmap colors the streamlines by the magnitude of the field, like Mathematica does by default
stream = figure[0, 0].add_stream(
    positions=positions,
    directions=directions,
    cmap="viridis",
)

figure.show()

# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
