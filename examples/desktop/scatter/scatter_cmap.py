"""
Scatter Plot
============
Example showing cmap change for scatter plot.
"""

# test_example = true

import fastplotlib as fpl
import numpy as np
from pathlib import Path
from sklearn.cluster import AgglomerativeClustering


fig = fpl.Figure()

data_path = Path(__file__).parent.parent.joinpath("data", "iris.npy")
data = np.load(data_path)

agg = AgglomerativeClustering(n_clusters=3)
agg.fit_predict(data)

scatter_graphic = fig[0, 0].add_scatter(
    data=data[:, :-1],  # use only xy data
    sizes=15,
    alpha=0.7,
    cmap="Set1",
    cmap_transform=agg.labels_  # use the labels as a transform to map colors from the colormap
)

fig.show()

fig.canvas.set_logical_size(800, 800)

fig[0, 0].auto_scale()

scatter_graphic.cmap = "tab10"


if __name__ == "__main__":
    print(__doc__)
    fpl.run()
