"""
Line Stack
==========

Example showing how to plot a stack of lines
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

import numpy as np
import fastplotlib as fpl


xs = np.linspace(0, np.pi * 10, 100)
# sine wave
ys = np.sin(xs)

data = np.column_stack([xs, ys])
multi_data = np.stack([data] * 10)

figure = fpl.Figure(size=(700, 560))

line_stack = figure[0, 0].add_line_stack(
    multi_data,  # shape: (10, 100, 2), i.e. [n_lines, n_points, xy]
    cmap="jet",  # applied along n_lines
    thickness=5,
    separation=1,  # spacing between lines along the separation axis, default separation along "y" axis
)

figure.show(maintain_aspect=False)


# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# please see our docs for using fastplotlib interactively in ipython and jupyter
if __name__ == "__main__":
    print(__doc__)
    fpl.run()
