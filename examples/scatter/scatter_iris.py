"""
Iris Scatter Plot
=================

Example showing scatter plot using sklearn iris dataset.
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'hidden'

import fastplotlib as fpl
import numpy as np
from pathlib import Path
import sys

figure = fpl.Figure(size=(700, 560))

current_file = Path(sys.argv[0]).resolve()

data_path = Path(__file__).parent.parent.joinpath("data", "iris.npy")
data = np.load(data_path)

n_points = 50
colors = ["yellow"] * n_points + ["cyan"] * n_points + ["magenta"] * n_points

scatter_graphic = figure[0, 0].add_scatter(data=data[:, :-1], sizes=6, alpha=0.7, colors=colors)

figure.show()


# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
