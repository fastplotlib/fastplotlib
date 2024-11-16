"""
Image Widget Pixel Timeseries
=============================

Use an ImageWidget to view a grayscale video and click on pixels to show their values
over time (timeseries)
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'animate 6s 20fps'

import numpy as np
import fastplotlib as fpl
import imageio.v3 as iio


# download and open video file
print("download and reading video file")
url = "https://caiman.flatironinstitute.org/~neuro/caiman_downloadables/demoMovieJ.tif"
url = "/home/kushal/caiman_data/example_movies/demoMovieJ.tif"
video = iio.imread(url)

iw = fpl.ImageWidget(
    video,
    cmap="viridis",
    figure_kwargs={"size": (700, 600)}
)
iw.show()

fig = fpl.Figure(size=(700, 400))

# add an initial point
row_ix, col_ix = 29, 65
timeseries = fig[0, 0].add_line(video[:, row_ix, col_ix], thickness=1.0)
point = iw.figure[0, 0].add_scatter(np.column_stack([col_ix, row_ix]), sizes=10, alpha=0.7, colors="magenta")

time_selector = timeseries.add_linear_selector()


@time_selector.add_event_handler("selection")
def set_time_from_selector(ev):
    iw.current_index = {"t": ev.get_selected_index()}


@iw.managed_graphics[0].add_event_handler("double_click")
def update_pixel(ev):
    col, row = ev.pick_info["index"]

    point.data[0, :2] = [col, row]
    timeseries.data[:, 1] = video[:, row, col]
    fig[0, 0].auto_scale(maintain_aspect=False)


fig.show(maintain_aspect=False)
fpl.run()
