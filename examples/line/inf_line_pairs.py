"""
Infinite Lines from Point Pairs
===============================

Define infinite lines directly from pairs of points using ``axis=None``. Each two consecutive
points define one line. Here pairs of points sampled around the unit circle are used to produce
lines that are roughly tangent to the circle.
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

import fastplotlib as fpl
import numpy as np

figure = fpl.Figure(size=(700, 560))

# an even number of points sampled around a circle; each consecutive pair of points defines an infinite line
t = np.linspace(0, 2 * np.pi, 64, endpoint=False)
xs = np.sin(t)
ys = np.cos(t)
positions = np.column_stack([xs, ys, np.zeros_like(xs)])

figure[0, 0].add_inf_line(positions, axis=None, cmap="hsv", thickness=2)
figure[0, 0].axes.intersection = (0, 0, 0)

figure.show()


# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
