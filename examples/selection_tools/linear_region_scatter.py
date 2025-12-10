"""
LinearRegionSelectors with ScatterGraphic
=========================================

Example showing how to use a `LinearRegionSelector` with a scatter plot. We demonstrate two use cases, a horizontal
LinearRegionSelector which selects along the x-axis and a vertical selector which moves along the y-axis.
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

import fastplotlib as fpl
import numpy as np

# names for out subplots
names = [
    ["scatter x", "scatter y"],
    ["zoomed x region", "zoomed y region"]
]

# 2 rows, 2 columns
figure = fpl.Figure(
    (2, 2),
    size=(700, 560),
    names=names,
)

scatter_x_data = (100*np.random.random_sample(size=(500, 2))).astype(np.float32)
scatter_y_data = (100*np.random.random_sample(size=(500, 2))).astype(np.float32)

# plot scatter data
scatter_x = figure[0, 0].add_scatter(scatter_x_data)
scatter_y = figure[0, 1].add_scatter(scatter_y_data)

# add linear selectors
selector_x = scatter_x.add_linear_region_selector((0, 100))  # default axis is "x"
selector_y = scatter_y.add_linear_region_selector(axis="y")

@selector_x.add_event_handler("selection")
def set_zoom_x(ev):
    """sets zoomed x selector data"""
    selected_data = ev.get_selected_data()
    figure[1, 0].clear()
    figure[1, 0].add_scatter(selected_data, sizes=10)
    figure[1, 0].auto_scale()


@selector_y.add_event_handler("selection")
def set_zoom_y(ev):
    """sets zoomed y selector data"""
    selected_data = ev.get_selected_data()
    figure[1, 1].clear()
    figure[1, 1].add_scatter(selected_data, sizes=10)
    figure[1, 1].auto_scale()

# set initial selection
selector_x.selection = (30, 60)
selector_y.selection = (30, 60)

figure.show(maintain_aspect=False)

# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
