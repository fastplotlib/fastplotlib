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


plot = fpl.Plot()
# to force a specific framework such as glfw:
# plot = fpl.Plot(canvas="glfw")

data_path = Path(__file__).parent.parent.joinpath("data", "iris.npy")
data = np.load(data_path)


agg = AgglomerativeClustering(n_clusters=3)

agg.fit_predict(data)


scatter_graphic = plot.add_scatter(
    data=data[:, :-1],
    sizes=15,
    alpha=0.7,
    cmap="Set1",
    cmap_values=agg.labels_
)

plot.show()

plot.canvas.set_logical_size(800, 800)

plot.auto_scale()

scatter_graphic.cmap = "tab10"


if __name__ == "__main__":
    print(__doc__)
    fpl.run()
