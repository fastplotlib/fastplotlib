"""
Visibility and Highlight Selector
=================================

Example with an image that contains time-varying signals. An ``ImageHighlightSelector`` is created with pre-loaded
options for either contour outlines or filled masks that spatially denote a unique signal in the image. A
``VisiblitySelector`` is used on a LineCollection. When the image is clicked, the closest spatial signal is highlighted
and the corresponding line is made visible. Shift + click to multi-select signals.
"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'screenshot'

from functools import partial
import numpy as np
from scipy.ndimage import binary_erosion
import fastplotlib as fpl
import cmap as cmap_lib

n_t = 500
n_y, n_x = 128, 128
n_circles = 32
radius = 4  # diameter 5

rng = np.random.default_rng(0)

# Random circle centers
centers = rng.integers(0, [n_y, n_x], size=(n_circles, 2))

yy, xx = np.ogrid[:n_y, :n_x]

movies_sessions = list()
contours_sessions = list()
signals_sessions = list()
centers_per_session = list()
indices_per_session = list()

for session_index in range(3):
    masks = []
    contours = []  # perimeter pixel coordinates per circle

    for cy, cx in centers:
        mask = (yy - cy) ** 2 + (xx - cx) ** 2 <= radius**2
        masks.append(mask)
        # Perimeter = filled mask minus its erosion
        perimeter = mask  # & ~binary_erosion(mask)
        contours.append(np.argwhere(perimeter))  # shape (K, 2), columns are [y, x]

    images = np.zeros((n_t, n_y, n_x), dtype=np.float32)
    t = np.linspace(0, 10 * np.pi, n_t)
    phases = 2 * np.pi * np.arange(n_circles) / n_circles

    signals = list()
    for j, mask in enumerate(masks):
        signal = np.sin(t + phases[j]).astype(np.float32)  # (n_t,)
        noise = rng.normal(0, 0.05, (n_t, mask.sum())).astype(np.float32)  # (n_t, K)
        signal = signal[:, None] + noise
        images[:, mask] += signal
        signals.append(signal.mean(axis=1))

    signals = np.stack(signals)

    # just to create diff indices per session
    local_indices = np.roll(np.arange(n_circles), shift=session_index)
    centers_per_session.append(centers[local_indices])

    indices_per_session.append(local_indices)

    movies_sessions.append(images)
    contours_sessions.append(contours)
    signals_sessions.append(signals)

extents = {
    "images-0": (0, 0.33, 0, 0.33),
    "signals-0": (0.33, 1, 0, 0.33),
    "images-1": (0, 0.33, 0.33, 0.67),
    "signals-1": (0.33, 1, 0.33, 0.67),
    "images-2": (0, 0.33, 0.67, 1),
    "signals-2": (0.33, 1, 0.67, 1),
}

ref_range = {"time": (0, n_t, 1)}
ndw = fpl.NDWidget(ref_range, extents=extents, size=(1300, 500))

def master_to_local_index(session_id: int, selection_indices: list[int]) -> int:
    return selection_indices


# image click changes the selection, can change the selection vector in any other way too
def image_clicked(session, ev):
    col, row = ev.pick_info["index"]

    local_index = np.argmin(
        np.linalg.norm(centers_per_session[session] - np.array([row, col]), axis=1)
    )

    # inverse transform
    master_index = indices_per_session[session][local_index]

    print(local_index, master_index)

    global sv

    if "Shift" in ev.modifiers:
        sv.append(master_index)
    else:
        sv.selection = [master_index]

    for subplot in ndw.figure:
        if "signals" in subplot.name:
            subplot.auto_scale()


sv = fpl.SelectionVector()
for session_index, (indices, movie, contours, signals) in enumerate(
    zip(indices_per_session, movies_sessions, contours_sessions, signals_sessions)
):
    ndi = ndw[f"images-{session_index}"].add_nd_image(
        movie,
        dims=("time", "m", "n"),
        spatial_dims=list("mn"),
    )

    ndi.graphic.cmap = "gray"

    ndt = ndw[f"signals-{session_index}"].add_nd_timeseries(
        fpl.utils.heatmap_to_positions(signals, xvals=np.arange(0, n_t)),
        dims=("l", "time", "d"),
        spatial_dims=("l", "time", "d"),
        x_range_mode="fixed",
        display_window=None,
    )

    # selectors per-session
    image_selector = fpl.ImageHighlightSelector(
        ndi.graphic,
        lut="tab10",
        selection_options={"pixels": contours},
        options_alpha=0.1,
        options_color="w",
        lut_wrap="repeat",
        alpha=0.7,
    )

    traces_visible_selector = fpl.VisibilitySelector(
        ndt.graphic, lut="tab10", lut_wrap="repeat"
    )

    # set the contour selectors on the images
    image_selector.add_graphic(ndi.graphic)
    ndi.graphic.add_event_handler(partial(image_clicked, session_index), "double_click")

    # add selectors to SelectionVector with mapping that corresponds to this session
    mapping = partial(master_to_local_index, session_index)
    sv.add_selector((image_selector, mapping))
    sv.add_selector((traces_visible_selector, mapping))

ndw.show()

fpl.loop.run()
