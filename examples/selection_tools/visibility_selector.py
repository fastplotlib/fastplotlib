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

masks = []
contours = []  # perimeter pixel coordinates per circle

for cy, cx in centers:
    mask = (yy - cy) ** 2 + (xx - cx) ** 2 <= radius**2
    masks.append(mask)
    # Perimeter = filled mask minus its erosion
    perimeter = mask# & ~binary_erosion(mask)
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

extents = {
    "images": (0, 0.3, 0, 1),
    "signals": (0.3, 1, 0, 1),
}

ref_range = {"time": (0, n_t, 1)}
ndw = fpl.NDWidget(ref_range, extents=extents, size=(1300, 500))

ndi = ndw["images"].add_nd_image(
    images,
    dims=("time", "m", "n"),
    spatial_dims=list("mn"),
)

ndi.graphic.cmap = "gray"

tab10_lut = cmap_lib.Colormap("tab10").lut(10)
image_selector = fpl.ImageHighlightSelector(
    ndi.graphic,
    lut=tab10_lut,
    selection_options={"pixels": contours},
    options_alpha=0.1,
    options_color="w",
    lut_wrap="repeat",
    alpha=0.7,
)

ndt = ndw["signals"].add_nd_timeseries(
    fpl.utils.heatmap_to_positions(signals, xvals=np.arange(0, n_t)),
    dims=("l", "time", "d"),
    spatial_dims=("l", "time", "d"),
    x_range_mode="fixed",
    display_window=None,
)


traces_visible_selector = fpl.VisibilitySelector(
    ndt.graphic, lut=tab10_lut, lut_wrap="repeat"
)

sv = fpl.SelectionVector()
sv.add_selector(image_selector)
sv.add_selector(traces_visible_selector)


# image click changes the selection, can change the selection vector in any other way too
def image_clicked(ev):
    col, row = ev.pick_info["index"]
    comp_index = np.argmin(np.linalg.norm(centers - np.array([row, col]), axis=1))

    global sv

    if "Shift" in ev.modifiers:
        sv.append(comp_index)
    else:
        sv.selection = [comp_index]
    ndw.figure["signals"].auto_scale()


# set the contour selectors on the images
image_selector.add_graphic(ndi.graphic)
ndi.graphic.add_event_handler(image_clicked, "double_click")


ndw.show()

fpl.loop.run()
