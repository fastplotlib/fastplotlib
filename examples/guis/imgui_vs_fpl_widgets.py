"""
ImGUI vs fastplotlib widgets
============================

The same movie and cell traces in two windows, one frame shared between them.

Left: a fastplotlib image with an ``imgui_bundle.implot`` trace panel docked under it.
Right: an ``NDWidget``, an ``NDImage`` over an ``NDTimeseries``, configured through
``global_config`` to look the same.

In both windows: drag pans, scroll zooms, shift+scroll zooms x only, alt+scroll zooms
y only. The cyan line is the shown frame: drag it, the slider, or the NDWidget's
slider and both windows follow.
"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'screenshot'

import glfw
import numpy as np
import pygfx
import fastplotlib as fpl
from fastplotlib.axes import Axes
from fastplotlib.layouts import Subplot
from fastplotlib.ui import ImguiWindow
from imgui_bundle import imgui, implot

def hex_to_imvec4(h: str, alpha: float = 1.0) -> imgui.ImVec4:
    """
    Convert a hex color string (e.g. #1f77b4) into DearImGui RGBA vectors.

    Replaces:

    trace_colors = [
        imgui.ImVec4(*(int(h[i : i + 2], 16) / 255.0 for i in (1, 3, 5)), 1.0)
        for h in colors
    ]
    """
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    a = int(h[6:8], 16) / 255.0 if len(h) == 8 else alpha
    return imgui.ImVec4(r, g, b, a)

# synthetic data: gaussian cells with calcium-like transients in a noisy movie
# replace this block with a real movie (T, Y, X), traces (n_cells, T) and centers (n_cells, xy)
rng = np.random.default_rng(0)
n_frames, n_rows, n_cols = 2_000, 128, 128
n_cells = 8
fs = 30.0  # Hz
t = np.arange(n_frames, dtype=np.float32) / fs

centers = rng.uniform(16, 112, size=(n_cells, 2)).astype(np.float32)
yy, xx = np.mgrid[0:n_rows, 0:n_cols]
footprints = np.exp(
    -((xx - centers[:, 0, None, None]) ** 2 + (yy - centers[:, 1, None, None]) ** 2)
    / (2 * 4.0**2)
).astype(np.float32)

spikes = rng.random((n_cells, n_frames)) < 0.01
kernel = np.exp(-np.arange(int(fs * 2)) / (fs * 0.5))
traces = np.stack([np.convolve(s, kernel)[:n_frames] for s in spikes]).astype(
    np.float32
)

movie = np.tensordot(traces.T, footprints, axes=1)
movie += rng.standard_normal(movie.shape, dtype=np.float32) * 0.1
vmin, vmax = np.percentile(movie[::100], (1.0, 99.5))

# implot's Deep colormap, so a cell has one color in both windows
palette = [
    "#4c72b0",
    "#dd8452",
    "#55a868",
    "#c44e52",
    "#8172b3",
    "#937860",
    "#da8bc3",
    "#8c8c8c",
    "#ccb974",
    "#64b5cd",
]
colors = [palette[i % len(palette)] for i in range(n_cells)]
labels = [f"cell {i}" for i in range(n_cells)]

# fastplotlib config: no toolbar, a thin frame, gray images, the image filling its subplot
fpl.style.compact()
Subplot.config.auto_scale.zoom = 1.0
fpl.Figure.config.show.axes_visible = False
fpl.ImageGraphic.config.init.cmap = "gray"
fpl.LineGraphic.config.init.thickness = 1.5
Axes.config.init.grids = False
Axes.config.init.color = "#c7ccd6"
Axes.config.init.tick_size = 6.0
Axes.config.init.line_width = 1.0

# implot config: the plot drawn straight onto the panel behind it, no frame, no grid
clear = imgui.ImVec4(0.0, 0.0, 0.0, 0.0)
plot_colors = {
    implot.Col_.frame_bg: clear,
    implot.Col_.plot_bg: clear,
    implot.Col_.plot_border: clear,
    implot.Col_.axis_grid: clear,
    implot.Col_.axis_tick: imgui.ImVec4(0.80, 0.82, 0.86, 0.35),
    implot.Col_.axis_text: imgui.ImVec4(0.78, 0.80, 0.84, 1.00),
    implot.Col_.legend_bg: imgui.ImVec4(0.04, 0.05, 0.06, 0.80),
    implot.Col_.legend_border: clear,
    implot.Col_.legend_text: imgui.ImVec4(0.88, 0.89, 0.92, 1.00),
    implot.Col_.inlay_text: imgui.ImVec4(0.80, 0.82, 0.86, 1.00),
}
cursor_color = imgui.ImVec4(0.0, 1.0, 1.0, 1.0)
trace_colors = [hex_to_imvec4(h) for h in colors]

window_size = (600, 900)
traces_height = 360
ndwidget_ui = 57 + 50

frame_index = 0

def seek(frame: int, push: bool = True):
    """Show ``frame`` in both windows; ``push`` also moves the NDWidget's slider."""
    global frame_index
    frame = int(min(max(frame, 0), n_frames - 1))
    if frame == frame_index:
        return
    frame_index = frame
    image.data = movie[frame]
    if push:
        ndw.indices.set({"time": float(t[frame])})


def follow(indices: dict):
    """The NDWidget moved: show its frame without pushing the value back."""
    seek(int(np.searchsorted(t, indices["time"])), push=False)


class ImplotTraces(ImguiWindow):
    """A frame slider over an implot line plot, one line per cell."""

    def __init__(self):
        super().__init__()
        self._fit = True

    def update(self):
        if implot.get_current_context() is None:
            implot.create_context()

        imgui.set_next_item_width(-imgui.FLT_MIN)
        changed, frame = imgui.slider_int(
            "##frame", frame_index, 0, n_frames - 1, "frame %d"
        )
        if changed:
            seek(frame)
        imgui.text_disabled(
            "drag pans · scroll zooms · shift+scroll x only · alt+scroll y only · "
            "double-click fits"
        )

        for col, color in plot_colors.items():
            implot.push_style_color(col, color)
        implot.push_style_var(implot.StyleVar_.plot_border_size, 0.0)

        if self._fit:
            implot.set_next_axes_to_fit()
            self._fit = False

        if implot.begin_plot("##traces", imgui.ImVec2(-1, -1), implot.Flags_.no_title):
            # implot has no axis lock while zooming, so the key locks the other axis
            io = imgui.get_io()
            none, locked = implot.AxisFlags_.none, implot.AxisFlags_.lock
            implot.setup_axes(
                "time (s)",
                "trace",
                locked if io.key_alt else none,
                locked if io.key_shift else none,
            )
            for label, ys, color in zip(labels, traces, trace_colors):
                spec = implot.Spec(line_weight=1.5)
                spec.line_color = color
                # one contiguous float64 row per line; xscale turns the index into seconds
                implot.plot_line(label, ys.astype(np.float64), 1.0 / fs, 0.0, spec)

            _moved, x, _clicked, _hovered, held = implot.drag_line_x(
                0, float(t[frame_index]), cursor_color, 1.5, 0, False, False, False
            )
            if held:
                seek(int(np.searchsorted(t, x)))
            implot.end_plot()

        implot.pop_style_var()
        implot.pop_style_color(len(plot_colors))


class AxisLockPanZoom(pygfx.PanZoomController):
    """pygfx's pan-zoom with shift+wheel zooming x only and alt+wheel y only, both
    still toward the mouse like the plain wheel.
    """

    _default_controls = {
        **pygfx.PanZoomController._default_controls,
        "shift+wheel": ("zoom_to_point", "push", (-0.001, 0.0)),
        "alt+wheel": ("zoom_to_point", "push", (0.0, -0.001)),
    }

    def _update_zoom_to_point(self, delta, *, screen_pos, rect):
        if isinstance(delta, (int, float)):
            delta = (delta, delta)
        fx, fy = 2 ** delta[0], 2 ** delta[1]
        self._set_camera_state(self._zoom(fx, fy, self._get_camera_state()))
        x, y, w, h = rect
        dx, dy = screen_pos[0] - x - w / 2, screen_pos[1] - y - h / 2
        vecx, vecy = self._get_camera_vecs(rect)
        pan = (dx * (1 - fx) / fx, dy * (1 - fy) / fy)
        self._update_pan(pan, vecx=vecx, vecy=vecy)


# left window: the image with the implot trace panel docked under it
# an extent instead of a grid, so the subplot carries no "(0, 0)" title
figure = fpl.Figure(extents=[(0.0, 1.0, 0.0, 1.0)], size=window_size)
image = figure[0].add_image(movie[0], vmin=vmin, vmax=vmax)
figure[0].add_scatter(centers, colors=colors, sizes=7)
figure.add_imgui_window(ImplotTraces(), location="bottom", size=traces_height)

# right window: the NDWidget, the movie over the traces, one time slider driving both
dt = float(t[1] - t[0])
# the image the same height as the implot window's, above the slider dock
split = (window_size[1] - traces_height) / (window_size[1] - ndwidget_ui)
ndw = fpl.NDWidget(
    ranges={"time": (0.0, float(t[-1]) + dt, dt)},
    extents=[(0.0, 1.0, 0.0, split), (0.0, 1.0, split, 1.0)],
    size=window_size,
)

ndw[0].add_nd_image(
    movie,
    ("time", "row", "col"),
    ("row", "col"),
    slider_maps={"time": t},
    compute_histogram=False,
    graphic_kwargs={"vmin": vmin, "vmax": vmax},
)
ndw[0].subplot.add_scatter(centers, colors=colors, sizes=7)

# fastplotlib takes [n_lines, n_points, xy]
xy = np.empty((n_cells, n_frames, 2), dtype=np.float32)
xy[..., 0] = t
xy[..., 1] = traces

# every datapoint uploaded and the camera free, as implot leaves it
ndw[1].add_nd_timeseries(
    xy,
    ("cell", "time", "xy"),
    ("cell", "time", "xy"),
    graphic_type=fpl.LineCollection,
    x_range_mode=None,
    display_window=None,
    max_display_datapoints=None,
    slider_maps={"time": t},
    colors=colors,
)
ndw[1].subplot.controller = AxisLockPanZoom()

# fastplotlib draws its axes inside the plot, so the labels stay small
axes = ndw[1].subplot.axes
for ruler, text in ((axes.x, "time (s)"), (axes.y, "trace")):
    ruler.label.set_text(text)
    ruler.label.font_size = 12

# the NDWidget's slider drives the implot window too
ndw.indices.add_event_handler(follow)

figure.show()
ndw.show()
# show() hides every axes; the trace plot keeps its ticks like implot's
ndw[1].subplot.axes.visible = True

figure.canvas.set_title("implot traces")
ndw.figure.canvas.set_title("fastplotlib NDTimeseries")

# put the two windows side by side
for canvas, x in ((figure.canvas, 40), (ndw.figure.canvas, 40 + window_size[0] + 20)):
    if hasattr(canvas, "_window"):
        glfw.set_window_pos(canvas._window, x, 60)


# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
