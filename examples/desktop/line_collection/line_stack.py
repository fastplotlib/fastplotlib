"""
Line stack
==========
Example showing how to plot a stack of lines
"""

# test_example = true

import numpy as np
import fastplotlib as fpl


xs = np.linspace(0, np.pi * 10, 100)
# sine wave
ys = np.sin(xs)

data = np.column_stack([xs, ys])
multi_data = np.stack([data] * 10)

fig = fpl.Figure()

line_stack = fig[0, 0].add_line_stack(
    multi_data,  # shape: (10, 100, 2), i.e. [n_lines, n_points, xy]
    cmap="jet",  # applied along n_lines
    thickness=5,
    separation=1,  # spacing between lines along the separation axis, default separation along "y" axis
)

fig.show(maintain_aspect=False)

fig.canvas.set_logical_size(900, 600)

if __name__ == "__main__":
    print(__doc__)
    fpl.run()
