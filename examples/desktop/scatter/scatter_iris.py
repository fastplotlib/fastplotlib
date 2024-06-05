"""
Iris Scatter Plot
=================

Example showing scatter plot using sklearn iris dataset.
"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'screenshot'

import fastplotlib as fpl
import numpy as np
from pathlib import Path
import sys

fig = fpl.Figure()

current_file = Path(sys.argv[0]).resolve()

data_path = Path(current_file.parent.parent.joinpath("data", "iris.npy"))
data = np.load(data_path)

n_points = 50
colors = ["yellow"] * n_points + ["cyan"] * n_points + ["magenta"] * n_points

scatter_graphic = fig[0, 0].add_scatter(data=data[:, :-1], sizes=6, alpha=0.7, colors=colors)

# set canvas variable for sphinx_gallery to properly generate examples
# NOT required for users
canvas = fig.canvas

fig.show()

fig.canvas.set_logical_size(700, 560)

fig[0, 0].auto_scale()

# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# please see our docs for using fastplotlib interactively in ipython and jupyter
if __name__ == "__main__":
    print(__doc__)
    fpl.run()