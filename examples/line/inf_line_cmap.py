"""
Infinite Lines Colormap
=======================

Apply a colormap across a set of infinite lines, one color per line.
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

import fastplotlib as fpl
from rendercanvas.auto import loop
import numpy as np

figure = fpl.Figure(size=(700, 560))

# vertical lines colored by a colormap, one color per line
positions = np.arange(10)
figure[0, 0].add_inf_line(positions, axis="x", cmap="viridis", thickness=3)

figure.show()


# NOTE: loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    loop.run()
