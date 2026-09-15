# NDWidget — browsing and synchronizing n-dimensional data

`fpl.NDWidget` is the answer whenever the user wants to **scroll through** n-dimensional data (time, z, trial,
channel) or wants **several datasets locked to one shared reference index**. It gives you a slider per extra
dimension, playback controls, async data fetching, and out-of-core windowing, for free. Requires
`imgui-bundle`.

Do not hand-roll sliders with ipywidgets or imgui, and do not write your own "current frame" state.

## The mental model

For each array you add, you:

1. **name every dimension** in array order → `dims`
2. **say which dims are rendered**, in display order → `display_dims`
3. everything left over becomes a **slider dim**

Slider positions live in **reference space** — real units, usually seconds — shared by every graphic
in the widget. Each array converts a reference value to its own index with `slider_maps`. That is
what lets a 30 Hz video and a 30 kHz recording sit on one slider.

## Minimal example

```python
import numpy as np
import fastplotlib as fpl

movie = np.random.rand(1000, 30, 512, 512).astype(np.float32)   # [time, z, row, col]

ndw = fpl.NDWidget(ranges={"time": (0, 1000, 1), "depth": (0, 30, 1)}, size=(700, 560))

ndw[0, 0].add_nd_image(
    movie,
    ("time", "depth", "row", "col"),   # every dim, in array order
    ("row", "col"),                    # the rendered dims, in display order
    name="movie",
)

ndw.show()

if __name__ == "__main__":
    fpl.loop.run()
```

`ranges` is `{dim_name: (start, stop, step)}` in reference units. `step` is what the step button
and playback advance by. A slider dim with no entry gets an auto range of `(0, size, 1)` **and a
warning** — always pass `ranges` explicitly.

## The dims you name decide everything

`NDWidget` is fundamentally an n-dimensional data viewer: **an arbitrary slice of an n-dimensional
array is mapped to an arbitrarily chosen graphical representation** — image, image volume, line,
scatter, or vectors. Which dims are rendered and which become sliders is entirely your choice of
`dims`/`display_dims`, and two graphics move together **if and only if they use the same dim name**.

Everything below follows from that one rule. None of it is a special feature.

### Multi-plane imaging

Several arrays each `[n_planes, n_timepoints, rows, cols]` — raw and dF/F, say. Name the dims
identically and both subplots share one plane slider and one time slider:

```python
ndw = fpl.NDWidget(
    ranges={"time": (0.0, 40.0, 1 / 10), "plane": (0, n_planes, 1)},
    shape=(1, 2), names=["raw", "dff"], size=(900, 450),
)

for name, arr in (("raw", raw), ("dff", dff)):
    ndw[name].add_nd_image(
        arr,
        ("plane", "time", "m", "n"),   # every dim, in array order
        ("m", "n"),                    # render one plane; `plane` and `time` become sliders
        slider_maps={"time": times},
        graphic_kwargs={"cmap": "gray"},
        name=name,
    )
```

To scroll the two **independently**, give the plane dim a different name in each —
`("plane_raw", "time", "m", "n")` and `("plane_dff", "time", "m", "n")`, with a range for each. Same
arrays, same code, two sliders instead of one.

To see **every plane at once**, slice the plane axis and give each its own subplot. `arr[i]` on a lazy
array is still lazy, so this stays out-of-core:

```python
ndw = fpl.NDWidget(
    ranges={"time": (0.0, 40.0, 1 / 10)}, shape=(2, 3),
    names=[[f"plane-{i}" for i in range(3)], [f"plane-{i}" for i in range(3, 6)]],
    size=(1000, 700),
)

for i in range(n_planes):
    ndw[f"plane-{i}"].add_nd_image(
        raw[i], ("time", "m", "n"), ("m", "n"),
        slider_maps={"time": times}, graphic_kwargs={"cmap": "gray"}, name=f"plane-{i}",
    )
```

### Multi-FOV imaging

`[n_fovs, n_timepoints, rows, cols]` is the same shape with a different meaning, so it is the same
code. One subplot with the FOV on a slider:

```python
ndw[0, 0].add_nd_image(fovs, ("fov", "time", "m", "n"), ("m", "n"),
                       slider_maps={"time": times}, graphic_kwargs={"cmap": "gray"})
```

or one subplot per FOV — which is what you want when **each FOV has its own frame timestamps**,
since each then gets its own `slider_maps` entry:

```python
for i in range(n_fovs):
    ndw[f"fov-{i}"].add_nd_image(
        fovs[i], ("time", "m", "n"), ("m", "n"),
        slider_maps={"time": fov_times[i]},     # this FOV's own frame times
        graphic_kwargs={"cmap": "gray"}, name=f"fov-{i}",
    )
```

### Combining them

Nothing stops you stacking the two. `[n_fovs, n_planes, n_timepoints, rows, cols]` with
`display_dims=("m", "n")` leaves three sliders:

```python
ndw = fpl.NDWidget(
    ranges={"time": (0.0, 10.0, 0.1), "fov": (0, n_fovs, 1), "plane": (0, n_planes, 1)},
    size=(600, 500),
)
ndw[0, 0].add_nd_image(data, ("fov", "plane", "time", "m", "n"), ("m", "n"),
                       slider_maps={"time": times})
ndw.indices = {"fov": 1, "plane": 2, "time": 5.0}
```

The same array can also appear under more than one representation. Here the movie subplot shows the
plane you are scrolled to, while the timeseries subplot draws every plane's mean at once, because
`plane` is a *spatial* dim there (`n_graphics`) rather than a slider dim:

```python
ndw["movie"].add_nd_image(raw, ("plane", "time", "m", "n"), ("m", "n"),
                          slider_maps={"time": times}, graphic_kwargs={"cmap": "gray"})

ndw["means"].add_nd_timeseries(
    fpl.utils.heatmap_to_positions(raw.mean(axis=(2, 3)), xvals=times),
    ("plane", "time", "xy"), ("plane", "time", "xy"),
    slider_maps={"time": times}, display_window=10.0, x_range_mode="auto", cmap="tab10",
)
```

Whether a dim is a slider or an axis of the drawing is the whole design decision. Make it
deliberately, and say which you chose when you hand the code over.

## Multi-modal: one reference space, many subplots

This is the pattern that matters. Name the subplots, lay them out with fractional `extents`, give each
modality its own `slider_maps` in seconds, and link the x axis of the time-series subplots.

```python
extents = {
    "video":  (0,   0.4, 0,   1),
    "traces": (0.4, 1,   0,   0.5),
    "raster": (0.4, 1,   0.5, 1),
}

ndw = fpl.NDWidget(
    ranges={"time": (0.0, 600.0, 1 / 30)},      # 10 minutes, 30 Hz steps
    extents=extents,
    size=(1400, 800),
)

ndw["video"].add_video(
    reader,                                      # a lazy frame-decoding object
    dims=("time", "m", "n"),
    display_dims=("m", "n"),
    slider_maps={"time": frame_timestamps},      # seconds -> frame index
    compute_histogram=False,
    name="video",
)

ndw["traces"].add_nd_timeseries(
    traces,                                      # [n_cells, n_samples, 2]
    ("cell", "time", "xy"),
    ("cell", "time", "xy"),
    slider_maps={"time": trace_timestamps},      # seconds -> sample index
    display_window=10.0,                         # render 10 seconds at a time
    cmap="tab10",
    x_range_mode="auto",
    name="traces",
)

for name in ("traces", "raster"):
    subplot = ndw.figure[name]
    subplot.controller.add_camera(subplot.camera, include_state={"x", "width"})

ndw.show(maintain_aspect=False)
```

To drive **separate windows** off one reference index, share the `ReferenceIndices`:

```python
ndw_main  = fpl.NDWidget(ranges={"time": (0, 600, 1 / 30)}, extents=extents, names=names)
ndw_ephys = fpl.NDWidget(indices=ndw_main.indices, names=["spikes"], size=(1400, 400))
```

Only the first passes `ranges`; the rest pass `indices=`.

### A complete multi-modal viewer

Behavior video, an audio spectrogram, a spike raster, a hand-scored ethogram and keypoint tracking,
all in one reference space in seconds, across two windows. Five different graphical representations of five
acquisition systems; the only thing tying them together is the dim named `"time"` and each
modality's own `slider_maps`.

```python
# 1. one reference range: the intersection of what every modality covers
start = max(vid.time[0], t_spec[0], counts.t[0])
stop = min(vid.time[-1], t_spec[-1], counts.t[-1])

extents = {                                   # fractions of the canvas, named subplots
    "video":    (0,    0.35, 0,    0.6),
    "keypoints":(0,    0.35, 0.6,  1),
    "spec":     (0.35, 1,    0,    0.3),
    "raster":   (0.35, 1,    0.3,  0.65),
    "ethogram": (0.35, 1,    0.65, 1),
}
ndw = fpl.NDWidget(ranges={"time": (start, stop, 1 / 30)}, extents=extents, size=(1500, 900))

# 2. video — YUV planes straight to the GPU, no per-frame RGB conversion
ndw["video"].add_video(
    vid, dims=("time", "m", "n"), display_dims=("m", "n"),
    slider_maps={"time": vid.time}, compute_histogram=False, name="frame",
)

# 3. pose tracking, overlaid on the same subplot, showing a 2 second display_window of positions
ndw["video"].add_nd_scatter(
    keypoints_xy, ("kp", "time", "xy"), ("kp", "time", "xy"),   # [n_keypoints, n_frames, 2]
    slider_maps={"time": vid.time}, display_window=2.0, cmap="tab10", sizes=8, name="keypoints",
)

# 4. spectrogram — a heatmap that stays on the shared reference index, with a real frequency axis
spec_ndg = ndw["spec"].add_nd_timeseries(
    np.dstack([np.broadcast_to(t_spec[None, :], spec.shape), spec]).astype(np.float32),
    ("freq", "time", "xy"), ("freq", "time", "xy"),
    graphic_type=fpl.ImageGraphic, slider_maps={"time": t_spec},
    display_window=5.0, x_range_mode="auto",
    graphic_kwargs={"cmap": "viridis", "metadata": {"f": f_spec}}, name="spec",
)

# 5. spike raster — pynapple does the binning, heatmap_to_positions does the reshape
ndw["raster"].add_nd_timeseries(
    fpl.utils.heatmap_to_positions(counts.values.T, xvals=counts.t),
    ("unit", "time", "xy"), ("unit", "time", "xy"),
    graphic_type=fpl.ImageGraphic, slider_maps={"time": counts.t},
    display_window=5.0, x_range_mode="auto",
    graphic_kwargs={"cmap": "gray_r"}, name="raster",
)

# 6. ethogram — integer state codes with a discrete colormap, so code k is always color k
eth_ndg = ndw["ethogram"].add_nd_timeseries(
    np.dstack([np.broadcast_to(eth_times[None], codes.shape), codes]).astype(np.float32),
    ("behavior", "time", "xy"), ("behavior", "time", "xy"),
    graphic_type=fpl.ImageGraphic, slider_maps={"time": eth_times},
    display_window=5.0, x_range_mode="auto",
    graphic_kwargs={"cmap": cmap.Colormap(["white", "green", "orange", "red"]),
                    "vmin": 0, "vmax": 3},
    name="ethogram",
)

# 7. link the time axis of every time-series subplot; each keeps its own y scale
for name in ("spec", "raster", "ethogram"):
    subplot = ndw.figure[name]
    subplot.controller.add_camera(subplot.camera, include_state={"x", "width"})
    subplot.camera.maintain_aspect = False

# 8. a row index is not a frequency or a behavior — say so in the axis and the tooltip
ndw.figure["spec"].axes.y.tick_format = (
    lambda v, lo, hi: f"{round(f_spec[min(max(round(v), 0), f_spec.size - 1)] / 1e3)} kHz"
)
spec_ndg.graphic.tooltip_format = lambda pi: f"{f_spec[pi['index'][1]] / 1e3:.1f} kHz"
eth_ndg.graphic.tooltip_format = lambda pi: BEHAVIORS[
    round(eth_ndg.graphic.data[pi["index"][1], pi["index"][0]])
]

cursor = fpl.Cursor()
cursor.add_subplot(ndw.figure["video"])

# 9. a second window on the same reference index
ndw_traces = fpl.NDWidget(indices=ndw.indices, names=["traces"], size=(1500, 300))
ndw_traces["traces"].add_nd_timeseries(
    fpl.utils.heatmap_to_positions(dff, xvals=frame_times),
    ("cell", "time", "xy"), ("cell", "time", "xy"),
    slider_maps={"time": frame_times}, display_window=5.0, x_range_mode="auto", cmap="tab10",
)

# 10. a control that re-runs the analysis, preserving the view
@ndw.figure["raster"].add_imgui_window(location="top", size=36, title=None)
def bin_size_ui(subplot):
    global bin_ms
    changed, new_ms = imgui.input_int("bin size (ms)", v=bin_ms, step=10)
    if changed:
        bin_ms = max(new_ms, 1)
        state = subplot.camera.get_state()
        counts = spikes.count(bin_size=bin_ms / 1000, time_units="s", ep=ep)
        ndg = ndw["raster"]["raster"]
        ndg.data = fpl.utils.heatmap_to_positions(counts.values.T, xvals=counts.t)
        ndg.slider_maps = {"time": counts.t}
        subplot.camera.set_state(state)

for subplot in ndw.figure:
    subplot.toolbar = False
ndw.figure["video"].axes.visible = False

ndw.show(maintain_aspect=False)
ndw_traces.show(maintain_aspect=False)

if __name__ == "__main__":
    fpl.loop.run()
```

Five things in there generalize to any multi-modal viewer:

- **Panels are named, laid out as fractions**, and addressed by name everywhere afterwards.
- **Each modality maps the shared reference index onto its own indices** with its own recorded timestamps.
  Nothing is resampled onto a common rate.
- **Anything heatmap-shaped goes through `heatmap_to_positions` + `graphic_type=fpl.ImageGraphic`**
  rather than `add_image`, so it keeps a real time axis and stays on the shared reference index.
- **A row index is never a physical quantity.** Convert it in `axes.<x>.tick_format` and in
  `tooltip_format`, and carry whatever they need in `graphic_kwargs={"metadata": ...}`.
- **A UI control recomputes through the domain library** and restores the camera state, instead of
  mutating an already-derived array.

## The `add_nd_*` methods

```python
add_nd_image(data, dims, display_dims, rgb_dim=None, window_funcs=None, window_order=None,
             spatial_func=None, compute_histogram=True, slider_maps=None,
             slicer_type=NDImageSlicer, colorspace="srgb", colorrange="full",
             name=None, graphic_kwargs=None)

add_video(data, dims, display_dims, rgb_dim=None, colorspace="yuv420p", colorrange="limited",
          slicer_type=VideoSlicer, window_funcs=None, window_order=None, spatial_func=None,
          compute_histogram=True, slider_maps=None, name=None, graphic_kwargs=None)

add_nd_timeseries(data, dims, display_dims, *, graphic_type=LineStack, x_range_mode="auto",
                  slicer=NDPositionsSlicer, display_window=10, window_funcs=None,
                  window_order=None, spatial_func=None, slider_maps=None,
                  max_display_datapoints=1000, datapoints_window_func=None,
                  colors=None, cmap=None, cmap_transform=None, cmap_range=None,
                  thickness=None, sizes=None, markers=None,
                  name=None, graphic_kwargs=None, slicer_kwargs=None)

add_nd_lines(...)     # same, graphic_type is LineCollection, no x_range_mode
add_nd_scatter(...)   # same, graphic_type is ScatterCollection, no thickness
add_nd_vectors(data, dims, display_dims, window_funcs=None, window_order=None,
               spatial_func=None, slider_maps=None, name=None, graphic_kwargs=None)
```

`display_dims` picks the graphic for images:

| `display_dims` | renders as |
|---|---|
| `(rows, cols)` | grayscale `ImageGraphic` |
| `(rows, cols, rgb_dim)` | RGB(A) `ImageGraphic` — you must also pass `rgb_dim=` |
| `(z, rows, cols)` | `ImageVolumeGraphic` — **currently broken, see Known issues** |
| a YUV `colorspace` | `ImageYUVGraphic` |

For positions and timeseries, `display_dims` is always
**`(n_graphics, p, value_dim)`** — how many traces, how many datapoints each (`p`), and the
coordinate dim (size 2 for xy, 3 for xyz). The dims need not be in that order in the array; the
slice is transposed for you.

`graphic_type` on `add_nd_timeseries` is `LineStack` (default), `LineCollection`,
`ScatterCollection`, `ScatterStack`, or **`fpl.ImageGraphic`** for a heatmap — one row per trace,
color from the y value. A heatmap needs a value dim of exactly 2. `fpl.utils.heatmap_to_positions`
converts `[n_rows, n_timepoints]` into the `[n_rows, n_timepoints, 2]` these expect.

`add_nd_timeseries` also adds a `LinearSelector` marking the current position of `p`; dragging it
sets the index for every graphic on that dim.

`graphic_kwargs` is passed to the underlying graphic, e.g.
`graphic_kwargs={"cmap": "gray", "interpolation": "linear", "metadata": {...}}`.

## `slider_maps` — get the units right or the plot is wrong

`{dim_name: array_or_callable}` mapping a reference value to that array's index.

```python
slider_maps={"time": frame_timestamps}          # array -> searchsorted for you
slider_maps={"time": lambda t: int(t * fs)}     # callable
slider_maps={"time": recording.get_times()}     # whatever the library gives you
```

- **Pass the recorded timestamps array**, not a nominal rate. Clocks drift and frames drop.
- **No entry means identity + round** — the reference value is used directly as an index. Correct
  only when the reference units *are* indices.
- The result is clamped into `[0, size)`, so an out-of-range value pins to an end silently rather
  than raising.
- The setter mutates the dict you pass (arrays are replaced by their bound `.searchsorted`, missing
  dims filled with identity), so pass a fresh dict or `.copy()` if you reuse one.

When several modalities cover different spans, the reference range is their **intersection**:
`start = max(all_starts)`, `stop = min(all_stops)`.

## Out-of-core: `display_window` and `max_display_datapoints`

On positions/timeseries, the datapoints dim `p` is both spatial and a slider dim:

- `display_window` — how much of `p` to render, **in `p`'s reference units** (e.g. `10.0` seconds).
  `None` renders everything. This is what makes a dataset bigger than VRAM viewable.
- `max_display_datapoints` (default 1000) — caps the rendered points per graphic by setting the
  *step* of the window slice. Raise it deliberately; the ephys examples use `1_000_000`.
- `x_range_mode="auto"` couples the camera to the window: panning or zooming sets the window width
  and centre. `"fixed"` sets the range from `display_window` only. `None` leaves the camera alone.

## `window_funcs` — reducing over a slider dim

```python
window_funcs={"time": (np.mean, 2.5)},   # average over 2.5 seconds around the current position
window_order=("time",),                  # only dims listed here actually apply
```

The function must accept `axis` and `keepdims` and **must not drop the dimension** — the windowed
dim reduces to size 1 but has to stay. `window_size` is in reference units.

`spatial_func` is applied to the rendered slice afterwards, e.g. a spatial filter.

`datapoints_window_func=(func, apply_dims, window_size)` reduces along `p` after the display window;
`func` takes only `axis`, and `apply_dims` names which coordinates it applies to (`"y"`, `"xy"`,
`"all"`, ...).

## Colors, colormaps and sizes: windowed or static

Decided from the value you pass, not from a keyword:

- **static** — one value for all graphics, `[n_graphics]` values, or an iterator such as
  `itertools.cycle(["jet", "viridis"])`. Set once.
- **windowed** — an array whose axis 1 spans the **full** `p` dim (`[n_graphics, p, ...]`), or a
  callable `f(data_slice, dw_slice) -> values`. Re-sliced with the data on every update, so it
  carries one value per *displayed* datapoint.

A callable is how you drive appearance from another signal, e.g. tracking confidence as alpha:

```python
def alpha_from_likelihood(data, dw_slice):
    p = dw_slice.stop - dw_slice.start
    colors = keypoint_colors[:, None, :].repeat(p, axis=1)   # [n_graphics, p, 4]
    colors[-1, :, -1] = likelihood[dw_slice]                 # alpha of the last keypoint
    return colors

ndw["video"].add_nd_scatter(..., colors=alpha_from_likelihood)
```

`colors` and `cmap` are mutually exclusive; setting one clears the other. A windowed array
`cmap_transform` takes its `cmap_range` from the transform's min/max over the **full** `p` dim, so a
point's color does not change as the window slides. A callable transform therefore needs an explicit
`cmap_range`.

## Reading and driving the index

```python
ndw.indices                                  # the shared ReferenceIndices
ndw.indices = {"time": 12.5}                 # jump (clamped; unlisted dims keep their value)
ndw.indices["time"]                          # current value for one dim
ndw.ranges                                   # {dim: range}
```

`ndw.indices.add_event_handler(fn, "indices")` also exists. **Do not use it to keep a graphic in
step with the sliders.** Anything that should follow the sliders belongs in an `NDGraphic`, so that
it goes through the same async fetching, windowing and index scheduling as everything else. A
handler on the `"indices"` event runs synchronously on every index change, so it blocks the render
loop and bypasses that scheduling — a slider drag goes from responsive to stuttering.

Use it only for things that are not data: logging, syncing an external device, updating a non-fastplotlib
widget. If you reach for it to draw something, subclass instead — see **Extending: custom slicers and
graphics** below.

## Getting at the graphic and the data

```python
ndg = ndw["traces"].add_nd_timeseries(..., graphic_kwargs={"cmap": "gray_r", "vmin": 0, "vmax": 5})

ndg.graphic                # the underlying LineStack / ImageGraphic / ScatterCollection
ndg.graphic.tooltip_format = lambda pick_info: "..."
ndg.data = new_array       # swap the data; dims and display_dims are kept
ndg.display_window = 30.0
ndg.graphic_type = fpl.ImageGraphic   # switch representation live
ndg.pause = True           # stop this graphic following the sliders

ndw[0, 0]["traces"]        # an NDGraphic by name
ndw.ndgraphics             # all of them, across every subplot
ndw.figure["traces"]       # the plain Subplot, for cameras/axes/imgui
```

Set graphic properties through the `NDPositions` wrapper (`ndg.colors`, `ndg.cmap`, `ndg.sizes`,
`ndg.thickness`, `ndg.markers`) when the value should be re-applied on every window update; set them
on `ndg.graphic` for a one-off change.

## Anti-patterns

| Do not | Do instead |
|---|---|
| build ipywidgets/imgui sliders for an nD array | `fpl.NDWidget` |
| keep your own `current_frame` and write `image.data = movie[i]` in a callback | `add_nd_image` / `add_video` with `slider_maps` |
| `fpl.ImageWidget` | `fpl.NDWidget` (`ImageWidget` is broken and unexported) |
| omit `ranges` and accept the auto-range warning if you're visualizing multi-modal data where each array has a different sampling rate | pass `ranges` in real units |
| convert time to indices on your own, e.g. `int(time * sampling_freq)`, when you have timestamps | `slider_maps={"time": timestamps}` |
| load a whole session and slice it in numpy | pass the lazy reader, and set `display_window` for positional data |
| `display_window=None` on a large dataset/array | a window in seconds; `None` reads everything |
| `compute_histogram=True` for video | `False` — it needs random frame access and is very slow |
| one `NDWidget` per modality with separate sliders | one `ranges`, then `indices=ndw.indices` for the rest |
| `add_nd_image` for a video file | use `add_video` and the `asyncvideo` library (https://pypi.org/project/asyncvideo/), YUV planes straight to the GPU, no per-frame RGB conversion, order of magnitude faster |
| a `for` loop over `ndg.graphic` to set a property every frame | pass the property to `add_nd_*` so it is re-applied by the window machinery |
| plotting a `[n_cells, n_timepoints]` heatmap array directly as an image | `fpl.utils.heatmap_to_positions` + `add_nd_timeseries(graphic_type=fpl.ImageGraphic)`, so it stays on the shared reference index |

## Custom data sources

`ndp_extras.Pandas` (available when pandas is installed) reads positional data from DataFrame
columns instead of an array — one `(x_col, y_col)` tuple per graphic, which is exactly the shape of
pose-tracking output. The third positional becomes the slicer's `columns`:

```python
ndw[0, 0].add_nd_scatter(
    df, ("l", "time", "d"),
    [(f"{k}_x", f"{k}_y") for k in keypoints],     # -> PandasSlicer(columns=...)
    slicer=ndp_extras.Pandas,
    slider_maps={"time": df["times"].values},
    display_window=5.0,
)
```

**This currently raises** — see Known issues. Until it is fixed, build the array yourself:

```python
xy = np.dstack([                                    # [n_keypoints, n_frames, 2]
    np.stack([df[f"{k}_x"] for k in keypoints]),
    np.stack([df[f"{k}_y"] for k in keypoints]),
]).astype(np.float32)
ndw[0, 0].add_nd_scatter(xy, ("kp", "time", "xy"), ("kp", "time", "xy"),
                         slider_maps={"time": df["times"].values}, display_window=5.0)
```

## Extending: custom slicers and graphics

Subclass `NDSlicer` for more customized data loading, and/or `NDGraphic` for more customized
rendering.

### `NDSlicer` — customized data loading

Write a slicer when you need one for your own specific objects, a lazy data loader, any other form
of accessor, or to create the data in a more customized way. `data` does not have to be an array —
the slicer only has to operate as if the `dims` exist and return a slice the graphic can render.

Subclass the slicer whose output the graphic expects: `NDImageSlicer` for images and volumes,
`NDPositionsSlicer` for lines/scatters/timeseries, `NDVectorsSlicer` for vectors.

This reads traces out of a `spikeinterface` recording, loading only the current display window into
RAM (adapted from `ephys_utils.py` in the neuro examples repo):

```python
import numpy as np
from spikeinterface import BaseRecording
from fastplotlib.widgets.nd_widget import NDPositionsSlicer


class RecordingSlicer(NDPositionsSlicer):
    @property
    def data(self) -> BaseRecording:
        return self._data

    @data.setter
    def data(self, recording: BaseRecording):
        self._data = recording

    @property
    def shape(self) -> dict[str, int]:
        # interpreted shape, keyed by dim name, in display order
        l, p, d = self.display_dims
        return {
            l: self.data.get_num_channels(),   # one graphic per channel
            p: self.data.get_num_samples(),    # the datapoints dim
            d: 2,                              # xy
        }

    async def get(self, indices) -> dict[str, np.ndarray]:
        # display window as array indices; slice.step comes from max_display_datapoints
        s = self._get_dw_slice(indices)

        xs = self.data.get_times()[s]
        ys = self.data.get_traces(start_frame=s.start, end_frame=s.stop)[:: s.step]

        # -> [n_channels, n_datapoints, xy]
        return {"data": np.stack([np.broadcast_to(xs[:, None], ys.shape), ys]).T}
```

```python
ndw["recording"].add_nd_timeseries(
    recording, ("l", "time", "d"), ("l", "time", "d"),
    slicer=RecordingSlicer,
    graphic_type=fpl.ImageGraphic,          # can be changed to a LineStack at runtime
    slider_maps={"time": lambda t: recording.time_to_sample_index(t)},
    display_window=0.05,
    x_range_mode="auto",
    graphic_kwargs={"cmap": "seismic", "vmin": -5, "vmax": 5},
)
```

What a subclass must provide:

- **`async def get(self, indices)`**, the one required method. `indices` is in reference-space units.
  `_get_dw_slice(indices)` returns the array slice for the current display window;
  `_ref_index_to_array_index(dim, value)` maps a single dim. Return a dict whose `"data"` key holds
  the array, shaped as `display_dims`.
- **`shape`**, a dict keyed by dim name, and **`data`** if the object is not an array.
  `_get_dw_slice` and `NDWSubplot._check_slider_dims` both read the dim sizes from `shape`.
- Blocking reads go in `run_in_thread_pool(self._executor, fn, ...)`; a reader that returns a future
  is awaited with `wait_for_future`. Doing the read inline blocks the render loop and the sliders
  stutter.
- Pass it as `slicer_type=` to `add_nd_image`/`add_video`, or `slicer=` to
  `add_nd_lines`/`add_nd_scatter`/`add_nd_timeseries`. Extra constructor arguments go through
  `slicer_kwargs=`, or as trailing positionals — that is how `PandasSlicer` receives `columns`.

### `NDGraphic` — customized rendering

Needed when no existing `NDGraphic` renders your slice, i.e. you want a representation that
`NDImage`, `NDPositions`, `NDTimeseries` and `NDVectors` do not cover — a mesh, a surface, a polygon
collection. Implement `_create_graphic()` to build the `Graphic` from the first slice and add it to
`self._nd_subplot.subplot`, and `_set_indices_(indices)` to write each new slice into that graphic
in place, allocating a new buffer only when the shape changes. Then add an `add_nd_<thing>()` to
`NDWSubplot` that calls `_check_slider_dims`, constructs it, appends it to `self._nd_graphics` and
returns it.

If you only need a different data source for an existing representation, subclass the slicer and
keep the graphic.

## Known issues

Verified against the current checkout. Work around them; do not try to fix them without asking.

1. **Volumes through `add_nd_image` raise.** `display_dims=(z, rows, cols)` hits
   `TypeError: Graphic.__init__() got an unexpected keyword argument 'colorspace'` — `_create_graphic`
   passes `colorspace` to every image class, and `ImageVolumeGraphic` does not take it. Until it is
   fixed, render `(rows, cols)` and leave `z` as a slider dim, or use a plain
   `figure[0, 0].add_image_volume(...)` outside the widget.

2. **`slicer=ndp_extras.Pandas` raises** from `NDWSubplot._check_slider_dims`, which treats the third
   positional as dim names rather than columns and then indexes `data.shape` with them
   (`IndexError: tuple index out of range`). Constructing `PandasSlicer(...)` directly works; only
   the `add_nd_*` route is broken. Use the array workaround above.

3. **Assigning `graphic.cmap` after construction desyncs the colorbar.** With
   `compute_histogram=True` (the default for `add_nd_image`), `ndg.graphic.cmap = ...` raises inside
   `ImguiColorbar._image_event_handler` (`Colormap.__eq__` on colormaps with different stop counts).
   `rendercanvas` swallows it, so the image updates and the colorbar silently does not. **Pass the
   colormap at construction instead**: `graphic_kwargs={"cmap": "gray_r", "vmin": 0, "vmax": 3}`.
   That path is clean, and it accepts a `cmap.Colormap` object as well as a name.
