"""
Infinite Lines Colormap Transform
=================================

Use a ``cmap_transform`` to color infinite lines by an associated value rather than by their sequential
order. Here each line at an x-position is colored according to the sine value at that x-axis position.
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

import fastplotlib as fpl
import numpy as np

figure = fpl.Figure(size=(700, 560))

# evenly spaced vertical lines
positions = np.linspace(0, 6 * np.pi, 32)

# color each line by an associated value using the colormap transform
values = np.sin(positions)
figure[0, 0].add_inf_line(
    positions, axis="x", cmap="plasma", cmap_transform=values, thickness=3
)

figure.show()


# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
