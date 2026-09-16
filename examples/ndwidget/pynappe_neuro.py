"""
Pynapple Multi-Modal Session
============================

Browse a pynapple session — a calcium movie, dF/F traces, spike times and scored behavior — on one
shared time axis in seconds.

Each object keeps its own sampling rate and its own timestamps. ``add_pynapple_obj`` picks the
slicer from the type of the object and takes the timebase from the object itself, so there is no
``slider_maps`` to write and no chance of pairing an object with the wrong slicer.

The floating window drives the properties that are backed by the metadata, so the same data can be
re-binned, re-ordered, re-colored and re-grouped without rebuilding the viewer.
"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'screenshot'

import numpy as np
import pynapple as nap
import fastplotlib as fpl
from imgui_bundle import imgui

fpl.style.compact()
fpl.style.light()

nap_slicers = fpl.nds_extras.Pynapple

rng = np.random.default_rng(0)
duration = 120.0  # seconds

# imaging at 10 Hz
frame_times = np.arange(0, duration, 1 / 10)
rows, cols = np.meshgrid(np.linspace(0, 1, 64), np.linspace(0, 1, 64))
movie = nap.TsdTensor(
    t=frame_times,
    d=np.stack(
        [np.sin(6 * rows + i / 8) * np.cos(6 * cols) for i in range(frame_times.size)]
    ).astype(np.float32),
)

# one dF/F trace per cell, each carrying the region it was recorded in and its depth in µm
cell_regions = ["V1", "M1", "V1", "M1", "V1", "M1", "V1", "M1"]
cell_depths = [310.0, 95.0, 260.0, 140.0, 405.0, 180.0, 220.0, 350.0]
dff = nap.TsdFrame(
    t=frame_times,
    d=np.stack(
        [
            np.sin(frame_times * (0.4 + 0.15 * i)) + rng.normal(0, 0.1, frame_times.size)
            for i in range(len(cell_regions))
        ],
        axis=1,
    ).astype(np.float32),
    metadata={"region": cell_regions, "depth": cell_depths},
)

# sorted units, on their own irregular timebase rather than the imaging frames
unit_rates = [4, 7, 11, 5, 18, 9, 22, 6, 13, 8]
units = nap.TsGroup(
    {i: nap.Ts(np.sort(rng.random(int(r * duration)) * duration)) for i, r in enumerate(unit_rates)},
    metadata={
        "cell_type": ["pE", "pI", "pE", "pE", "pI", "pE", "pI", "pE", "pE", "pI"],
        "depth": [820.0, 240.0, 610.0, 155.0, 970.0, 430.0, 705.0, 60.0, 340.0, 520.0],
    },
)

# hand-scored behavior, as epochs rather than a sampled signal
behavior = nap.IntervalSet(
    start=[3.0, 22.0, 41.0, 58.0, 77.0, 96.0],
    end=[19.0, 37.0, 55.0, 74.0, 92.0, 114.0],
    metadata={
        "state": ["run", "rest", "groom", "run", "rest", "run"],
        "block": ["early", "early", "early", "late", "late", "late"],
    },
)

# the reference range is the *intersection* of what every modality covers. Past the end of the
# shortest one the sliders keep moving while that graphic is pinned to its last sample, which
# looks like real data. `step` is the playback increment, here the 10 Hz imaging period.
ranges = nap_slicers.ranges_from_time_support(movie, dff, units, behavior)

extents = {
    "movie": (0, 0.32, 0, 1),
    "dff": (0.32, 1, 0, 0.28),
    "rate": (0.32, 1, 0.28, 0.54),
    "spikes": (0.32, 1, 0.54, 0.76),
    "behavior": (0.32, 1, 0.76, 1),
}

ndw = fpl.NDWidget(ranges=ranges, extents=extents, size=(1300, 900))

ndw["movie"].add_pynapple_obj(
    movie,
    ("time", "m", "n"),
    ("m", "n"),
    compute_histogram=False,
    graphic_kwargs={"cmap": "gray"},
    name="movie",
)

# ordered by depth and colored by region, and the colors follow the order
dff_ndg = ndw["dff"].add_pynapple_obj(
    dff,
    ("cell", "time", "xy"),
    ("cell", "time", "xy"),
    display_window=20.0,
    sort_by="depth",
    color_by="region",
    name="dff",
)

# a TsGroup defaults to firing rate in Hz, on a bin grid anchored at the start of the recording so
# the edges stay put as you scroll
rate_ndg = ndw["rate"].add_pynapple_obj(
    units,
    ("unit", "time", "xy"),
    ("unit", "time", "xy"),
    bin_size=0.05,
    display_window=20.0,
    sort_by="depth",
    graphic_kwargs={"cmap": "gray_r"},
    name="rate",
)

# the same units as individual spikes, placed on the probe by depth rather than by unit key
spikes_ndg = ndw["spikes"].add_pynapple_obj(
    units,
    ("l", "time", "xy"),
    ("l", "time", "xy"),
    slicer=nap_slicers.TsGroupSpikes,
    y="depth",
    display_window=20.0,
    colors="cyan",
    sizes=3,
    name="spikes",
)

# one row per behavioral state, valued by how much of each bin that state covers, so an epoch
# shorter than a bin fades in rather than disappearing
eth_ndg = ndw["behavior"].add_pynapple_obj(
    behavior,
    ("state", "time", "xy"),
    ("state", "time", "xy"),
    column="state",
    display_window=20.0,
    graphic_kwargs={"cmap": "magma", "vmin": 0, "vmax": 1},
    name="ethogram",
)


# a row index is not a state, so label the rows with the names. Read the categories on every call
# rather than capturing them, since the `column` control below changes them.
def state_label(value, lower, upper):
    categories = eth_ndg.slicer.categories
    return categories[min(max(round(value), 0), categories.size - 1)]


ndw.figure["behavior"].axes.y.tick_format = state_label


def metadata_combo(label, current, columns, allow_none=True):
    """a combo over the metadata columns, returning ``(changed, column)``"""
    options = [None, *columns] if allow_none else list(columns)
    changed, index = imgui.combo(
        label, options.index(current), ["—" if o is None else str(o) for o in options]
    )

    return changed, options[index]


@ndw.figure.add_imgui_window(
    location="floating",
    title="pynapple",
    window_flags=imgui.WindowFlags_.always_auto_resize,
)
def controls():
    imgui.separator_text("dF/F traces")

    changed, column = metadata_combo("color by", dff_ndg.color_by, dff.metadata_columns)
    if changed:
        dff_ndg.color_by = column

    changed, column = metadata_combo("sort by##dff", dff_ndg.sort_by, dff.metadata_columns)
    if changed:
        dff_ndg.sort_by = column

    imgui.separator_text("firing rate")

    imgui.set_next_item_width(160)
    changed, value = imgui.slider_float(
        "bin size (s)",
        rate_ndg.bin_size,
        0.001,
        2.0,
        flags=imgui.SliderFlags_.logarithmic,
    )
    if changed:
        rate_ndg.bin_size = value

    # over a wide window the rendered bins are widened to a multiple of `bin_size` rather than
    # decimated, so say which bins are actually on screen
    rendered = rate_ndg.slicer.effective_bin_size(rate_ndg.display_window)
    imgui.text(f"rendered: {rendered * 1e3:.1f} ms x {rate_ndg.slicer.n_bins} bins")

    changed, column = metadata_combo("sort by##rate", rate_ndg.sort_by, units.metadata_columns)
    if changed:
        rate_ndg.sort_by = column

    imgui.separator_text("spike raster")

    changed, column = metadata_combo("row from", spikes_ndg.y, units.metadata_columns)
    if changed:
        spikes_ndg.y = column

    imgui.separator_text("ethogram")

    changed, column = metadata_combo(
        "rows from", eth_ndg.column, behavior.metadata_columns, allow_none=False
    )
    if changed:
        eth_ndg.column = column


for subplot_name in ("dff", "rate", "spikes", "behavior"):
    subplot = ndw.figure[subplot_name]
    subplot.controller.add_camera(subplot.camera, include_state={"x", "width"})
    subplot.camera.maintain_aspect = False

ndw.figure["movie"].axes.visible = False

ndw.show(maintain_aspect=False)
figure = ndw.figure


# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
