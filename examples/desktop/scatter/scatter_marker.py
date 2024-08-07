"""
Scatter Plot Markers
====================

Example showing scatter plot using different markers
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

import fastplotlib as fpl
import pygfx
import numpy as np
from sklearn.cluster import AgglomerativeClustering
from sklearn import datasets


iris = datasets.load_iris()
data = iris["data"]
targets = iris["target"]

agg = AgglomerativeClustering(n_clusters=3)
agg.fit_predict(data)

figure = fpl.Figure()

# markers to denote the real label
markers = ["circle", "cross", "square"]


# colors to denote the clustering results
tab10 = fpl.utils.make_colors(3, "tab10")
label_colors = {i: pygfx.Color(tab10[i]).hex for i in range(3)}
# makes a list of hex strings by mapping the labels using the above dict
colors = np.fromiter(map(label_colors.get, agg.labels_), dtype="<U7")

for marker, target in zip(markers, np.unique(targets)):
    figure[0, 0].add_scatter(
        data=data[targets == target, :-1].astype(np.float32),
        sizes=15,
        alpha=0.5,
        colors=colors[targets == target],
        marker=marker,
    )

figure.show()

figure.canvas.set_logical_size(700, 560)

figure[0, 0].auto_scale()

# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# please see our docs for using fastplotlib interactively in ipython and jupyter
if __name__ == "__main__":
    print(__doc__)
    fpl.run()