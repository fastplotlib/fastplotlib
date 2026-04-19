"""
Highlight Selector
==================

NDWidget with a time-varying 100x100 image (two circles driven by sine/cosine)
and a heatmap of all pixel timeseries. Clicking a row of the heatmap highlights
that row and the corresponding pixel on the image.
Shift-click appends; plain click replaces the selection.
"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'screenshot'

import numpy as np
import fastplotlib as fpl
from fastplotlib.graphics import ImageGraphic
from fastplotlib.graphics.selectors import ImageHighlightSelector
from fastplotlib.utils.functions import heatmap_to_positions

# --- synthetic data ---
n_t = 100
n_y, n_x = 100, 100

rng = np.random.default_rng(0)
vol = np.zeros((n_t, n_y, n_x), dtype=np.float32)

yy, xx = np.ogrid[:n_y, :n_x]
mask1 = (yy - 30) ** 2 + (xx - 30) ** 2 < 15**2
mask2 = (yy - 70) ** 2 + (xx - 70) ** 2 < 15**2

t = np.linspace(0, 2 * np.pi, n_t)
for i in range(n_t):
    vol[i, mask1] = np.sin(t[i]) + rng.normal(0, 0.05, mask1.sum())
    vol[i, mask2] = np.cos(t[i]) + rng.normal(0, 0.05, mask2.sum())

# heatmap: (n_pixels, n_t), then convert to positions for add_nd_timeseries
heatmap = vol.reshape(n_t, n_y * n_x).T.astype(np.float32)  # (n_pixels, n_t)
xvals = np.arange(n_t, dtype=np.float32)
heatmap_pos = heatmap_to_positions(heatmap, xvals)  # (n_pixels, n_t, 2)

# --- layout ---
ndw = fpl.NDWidget(ref_ranges={"t": (0, n_t, 1)}, shape=(1, 2), size=(1400, 560))

nd_img = ndw[0, 0].add_nd_image(vol, ("t", "y", "x"), ("y", "x"), name="image")

nd_hm = ndw[0, 1].add_nd_timeseries(
    heatmap_pos,
    dims=("pixel", "t", "xy"),
    spatial_dims=("pixel", "t", "xy"),
    graphic_type=ImageGraphic,
    x_range_mode="fixed",
    display_window=None,
    name="heatmap",
)

# --- highlight selectors ---
img_sel = ImageHighlightSelector(color="cyan", alpha=0.8)
img_sel.add_graphic(nd_img.graphic)

hm_sel = ImageHighlightSelector(color="cyan", alpha=0.8)
hm_sel.add_graphic(nd_hm.graphic)


@nd_hm.graphic.add_event_handler("double_click")
def on_heatmap_click(ev):
    idx = ev.pick_info.get("index")
    if idx is None:
        return
    # index = (col, row) = (timepoint, pixel_idx)
    pixel_idx = idx[1]
    row = pixel_idx // n_x
    col = pixel_idx % n_x

    if "Shift" in ev.modifiers:
        hm_sel.append("rows", pixel_idx)
        img_sel.append("pixels", np.array([[row, col]]))
        print(hm_sel.selection)
    else:
        hm_sel.selection = {"rows": [pixel_idx]}
        img_sel.selection = {"pixels": [np.array([[row, col]])]}


ndw.show(maintain_aspect=False)

# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
