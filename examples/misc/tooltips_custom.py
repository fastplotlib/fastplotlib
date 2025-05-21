"""
Tooltips Customization
======================

Customize the information displayed in a tooltip. This example uses the Iris dataset and sets the tooltip to display
the species and cluster label of the point that is being hovered by the mouse pointer.
"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'screenshot'


import fastplotlib as fpl
from sklearn.cluster import AgglomerativeClustering
from sklearn import datasets


figure = fpl.Figure(size=(700, 560))

dataset = datasets.load_iris()
data = dataset["data"]

agg = AgglomerativeClustering(n_clusters=3)
agg.fit_predict(data)

scatter_graphic = figure[0, 0].add_scatter(
    data=data[:, :-1],  # use only xy data
    sizes=15,
    cmap="Set1",
    cmap_transform=agg.labels_  # use the labels as a transform to map colors from the colormap
)


def tooltip_info(ev) -> str:
    # get index of the scatter point that is being hovered
    index = ev.pick_info["vertex_index"]

    # get the species name
    target = dataset["target"][index]
    cluster = agg.labels_[index]
    info = f"species: {dataset['target_names'][target]}\ncluster: {cluster}"

    # return this string to display it in the tooltip
    return info


figure.tooltip_manager.register(scatter_graphic, custom_info=tooltip_info)

figure.show()


if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
