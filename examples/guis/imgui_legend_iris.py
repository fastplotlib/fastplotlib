"""
ImGUI Legend with Markers
=========================

The iris dataset, with the species of each sample shown by color and the k-means cluster it was
assigned to shown by marker shape. A feature that is not the same for every datapoint needs a
label for each of its values, so the legend has an entry per species and an entry per cluster.
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

import numpy as np
import fastplotlib as fpl
from fastplotlib.ui import Legend
from sklearn.cluster import KMeans
from sklearn import datasets

figure = fpl.Figure(size=(700, 560))

iris = datasets.load_iris()

# one marker shape per predicted cluster
kmeans = KMeans(n_clusters=3, n_init=10, random_state=0).fit(iris["data"])
markers = np.asarray(["circle", "square", "diamond"])[kmeans.labels_]

scatter = figure[0, 0].add_scatter(
    data=iris["data"][:, :2],  # sepal length and width
    sizes=12,
    cmap="tab10",
    cmap_transform=iris["target"],  # species
    markers=markers,
    alpha=0.5,
)
# qualitative colormap, span its full range so that species k always gets color k
scatter.cmap_range = (0, scatter.cmap.num_colors)

# the species entries are colored by the colormap, the cluster entries show the marker shapes
legend = Legend(
    [
        scatter.create_legend_item(
            label="iris",
            cmap_transform_labels={
                i: str(name) for i, name in enumerate(iris["target_names"])
            },
            markers_labels={
                "circle": "cluster 0",
                "square": "cluster 1",
                "diamond": "cluster 2",
            },
        )
    ]
)

# a floating legend is drawn over the plot and can be dragged around, it reserves no canvas space
figure.add_imgui_window(
    legend, location="floating", rect=(0.8, 0.1, 0, 0), title="legend"
)

figure.show(maintain_aspect=False)


# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
