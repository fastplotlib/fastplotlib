"""
Polygon Selectors with ScatterGraphic
=====================================

Example showing how to use a `PolygonSelector` with a scatter plot.
"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'screenshot'

import numpy as np
import fastplotlib as fpl

# create a figure
figure = fpl.Figure(
    (1, 2),
    size=(700, 560),
    names=["scatter", "zoomed selection"],
)

xys = (100 * np.random.random_sample(size=(2000, 2))).astype(np.float32)

# add image
scatter = figure[0, 0].add_scatter(xys, cmap="jet", sizes=4)

# add polygon selector to scatter graphic
polygon_selector = scatter.add_polygon_selector()

# add event handler to highlight selected indices and display selected data in zoomed plot
@polygon_selector.add_event_handler("selection")
def color_indices(ev):
    figure[0, 1].clear()
    scatter.cmap = "jet"
    scatter.sizes = 4
    ixs = ev.get_selected_indices()
    if ixs.size == 0:
        return
    scatter.colors[ixs] = 'w'
    scatter.sizes[ixs] = 8
    figure[0, 1].add_scatter(ev.get_selected_data(), sizes=16)
    figure[0, 1].auto_scale()

figure.show()

# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
