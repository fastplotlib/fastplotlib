"""
Scatter Plot
============
Example showing cmap change for scatter plot.
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

import fastplotlib as fpl
import numpy as np
from pathlib import Path
from sklearn.cluster import AgglomerativeClustering
import sys

fig = fpl.Figure()

current_file = Path(sys.argv[0]).resolve()

data_path = Path(current_file.parent.parent.joinpath("data", "iris.npy"))
data = np.load(data_path)

agg = AgglomerativeClustering(n_clusters=3)
agg.fit_predict(data)

scatter_graphic = fig[0, 0].add_scatter(
    data=data[:, :-1], sizes=15, alpha=0.7, cmap="Set1", cmap_values=agg.labels_
)

# set canvas variable for sphinx_gallery to properly generate examples
# NOT required for users
canvas = fig.canvas

fig.show()

fig.canvas.set_logical_size(800, 800)

fig[0, 0].auto_scale()

scatter_graphic.cmap = "tab10"

# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# please see our docs for using fastplotlib interactively in ipython and jupyter
if __name__ == "__main__":
    print(__doc__)
    fpl.run()
