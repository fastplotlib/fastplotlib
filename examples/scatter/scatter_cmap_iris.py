"""
Iris Scatter Colormap
=====================

Example showing cmap change for scatter plot.
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

import fastplotlib as fpl
from sklearn.cluster import AgglomerativeClustering
from sklearn import datasets


figure = fpl.Figure(size=(700, 560))

data = datasets.load_iris()["data"]

agg = AgglomerativeClustering(n_clusters=3)
agg.fit_predict(data)

scatter_graphic = figure[
    0, 0
].add_scatter(
    data=data[:, :-1],  # use only xy data
    sizes=15,
    alpha=0.7,
    cmap="Set1",
    cmap_transform=agg.labels_,  # use the labels as a transform to map colors from the colormap
)

figure.show()

scatter_graphic.cmap = "tab10"


if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
