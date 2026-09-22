NDWidget data model
===================

The problem
-----------

Scientific data is n-dimensional. A volumetric time-lapse microscopy acquisition is (time, z, channel, rows,
columns), an MRI volume is (x, y, z, time), a climate model writes (time, level, latitude, longitude), and
behavior point tracking gives (keypoints, frames, xy).

Different instruments produce arrays of different shapes, sampled at different rates, i.e. multi modal data
which has to be visualized together.

Systems neuroscience probably produces the most complex multi-modal n-dimensional data of any scientific
discipline. A single session can draw on calcium imaging, electrophysiology and behavior tracking at the same
time: a movie of shape :math:`\mathbb{R}^{T \times Z \times M \times N}` (time, depth, rows, columns), traces
of shape :math:`\mathbb{R}^{K \times T}` (channels, samples), a behavior video, the keypoints tracked in it of
shape :math:`\mathbb{R}^{K \times T \times 2}` (keypoints, frames, xy), and the spike times of sorted units.
Each comes from a different acquisition system with its own sampling rate.

Existing tools each cover part of this. Domain-specific applications such as Suite2p, Phy and SimBA give a
fixed set of visualizations for one analysis pipeline, but are difficult to extend and not composable.
Multi-modal environments such as NWB Widgets and Bento link neural and behavioral views, but those views are
hard-coded and tied to particular data formats. General-purpose plotting libraries such as pyqtgraph, Plotly,
Bokeh and HoloViews are flexible for tabular data, but leave n-dimensional slicing, cross-modality
coordination and graphical update logic to be written by hand as callbacks. Image-focused tools such as
napari and ImageJ are built for imaging data rather than for timeseries representations or for coordination
across heterogeneously sampled data.

The ``NDWidget`` uses a coordination model to provide a declarative API. You declare what each dimension of
each array means and which of those dimensions are drawn, and the widget works out the rest: slicing, mapping
from a slider position onto each array's own indices, windowing, asynchronous reads, transferring CUDA
arrays, and which graphics have to update. It also manages spatial coordinates to make timeseries data easier
to explore, such as the auto range mode and out-of-core rendering, where only the slices needed for the
current view are read so that arrays can be lazy and far larger than RAM or VRAM. The graphical
representation is not fixed by the shape of the data, so the same array can be drawn as a line collection, a
stack, a scatter or a heatmap, and the representation can be changed while the widget is running.

``NDWidget`` requires ``imgui-bundle``, install it with ``pip install "fastplotlib[imgui]"``.

The data model
--------------

For each nd array you want to view, you must declare:

* ``dims``: the name of every dimension of the array, in the order in which it appears in the array
* ``display_dims``: the dimensions to render, in display order, which is the order that corresponds to the
  rendered representation, ``[rows, cols]`` or ``[depth, rows, cols]`` for images and :math:`[\ell, p, d]`
  for positional data

Every dimension that is not rendered becomes a **slider dim** and is given a slider. A 4D movie displayed as a
2D image therefore leaves a slider for time and a slider for depth::

    ndw[0, 0].add_nd_image(
        movie,                            # data
        ("time", "depth", "row", "col"),  # dims
        ("row", "col"),                   # display_dims
    )

The dimensions do not have to appear in display order in the array. ``dims`` names them in the order they
appear and ``display_dims`` gives the order they are drawn in, so an array declared as
``("col", "depth", "row", "time")`` and displayed as ``("row", "col")`` is transposed for you.

Positional data, which covers lines, scatters and heatmaps, is an array of the form

.. math::

    A \in \mathbb{R}^{s_1 \times \cdots \times s_n \times \ell \times p \times d}

where :math:`s_1, \ldots, s_n` are the slider dims, any navigable dimension such as time, trial, depth or
experimental condition, :math:`\ell` is the number of graphical elements, i.e. the lines or scatters in the
collection or the rows of the heatmap, :math:`p` is the number of datapoints in each of them, often the
number of sampled timepoints, and :math:`d \in \{2, 3\}` holds the :math:`(x, y)` or :math:`(x, y, z)`
coordinate of a datapoint.

Image data is an array of the form

.. math::

    M \in \mathbb{R}^{s_1 \times \cdots \times s_n \times r \times c \times v}

where :math:`r` and :math:`c` are the rows and columns of the image, and :math:`v \in \{3, 4\}` is an
optional RGB(A) dimension that is declared with ``rgb_dim``. Rendering :math:`(z, r, c)` gives a volume
instead of a 2D image.

Vector data is an array of the form

.. math::

    V \in \mathbb{R}^{s_1 \times \cdots \times s_n \times k \times 2 \times d}

of :math:`k` vectors, where the size-2 dimension holds a position at index ``0`` and a direction at index
``1``.

Each slider dim is indexed at a single value, so given an index :math:`\lambda_j` along each slider dim the
rendered slice of a positional array is

.. math::

    S_A(\lambda) = A\left[\lambda_1, \ldots, \lambda_n,\ :,\ :,\ :\right] \in
    \mathbb{R}^{\ell \times p \times d}

and of an image array is

.. math::

    S_M(\lambda) = M\left[\lambda_1, \ldots, \lambda_n,\ :,\ :,\ :\right] \in \mathbb{R}^{r \times c \times v}

after which the slice is transposed to display order. For positional data :math:`p` is both rendered and
navigable, so it is windowed.

The slice is then mapped onto a graphical representation,

.. math::

    G : \mathbb{R}^{\ell \times p \times d} \to \{\text{LineCollection},\ \text{LineStack},\
    \text{ScatterCollection},\ \text{ScatterStack},\ \text{ImageGraphic}\}

for positional data and

.. math::

    G : \mathbb{R}^{r \times c \times v} \to \{\text{ImageGraphic},\ \text{ImageYUVGraphic},\
    \text{ImageVolumeGraphic}\}

for images. The shape of the slice does not determine :math:`G`. For images it follows from
``display_dims`` and ``colorspace``, and for positional data it is declared with ``graphic_type`` which is
mutable at runtime.

Reference space
---------------

A slider position is not an array index, it is a value in **reference units**, the scientific units of that
dimension, such as seconds, milliseconds, depth in microns, frequency in Hz, etc. The reference index is

.. math::

    \Lambda = (\Lambda_1, \ldots, \Lambda_n) \in \mathbb{U}^{n}

with one value :math:`\Lambda_j \in \mathbb{U}` for each slider dim. Every graphic in the widget shares it.

Each slider dim needs a range in these units. ``start`` and ``stop`` set the start and stop positions of the
slider for that dimension, and ``step`` is the increment used by the step buttons and by playback::

    ndw = fpl.NDWidget(ranges={"time": (0.0, 600.0, 1 / 30)})

For each array and each of its slider dims we define a mapping

.. math::

    \Phi_j : \mathbb{U} \to \mathbb{N}, \qquad \lambda_j = \Phi_j(\Lambda_j)

from a reference value onto an index of that array, declared as ``slider_maps``. An array of reference
values, such as timestamps, is used through its ``searchsorted``. An arbitrary callable that defines a
mapping can also be used. If a mapping isn't provided for a dimension, then the identity mapping is used,
i.e. the current reference index is used directly as an integer array index. The result is clamped into
:math:`[0, \text{size} - 1]`.

:math:`\Phi` is what lets arrays that were sampled at different rates share one slider::

    ndw["video"].add_video(
        video,                # data
        ("time", "m", "n"),   # dims
        ("m", "n"),           # display_dims
        slider_maps={"time": frame_times},
    )

    ndw["traces"].add_nd_timeseries(
        traces,                  # data
        ("l", "time", "d"),      # dims
        ("l", "time", "d"),      # display_dims
        slider_maps={"time": sample_times},
    )

Both of these declare a dim named ``"time"`` and each one provides its own timestamps, so a slider position
of 30 seconds resolves to frame 900 in a 30 Hz video and to sample 900,000 in a 30 kHz recording. Nothing is
resampled onto a common rate, and no modality is expressed in the indices of another.

The current reference index is ``ndw.indices``. Assigning to it moves the sliders and re-renders every
graphic that declares the dims given, and values are clamped to the range of their dim::

    ndw.indices = {"time": 12.5}
    ndw.indices["time"]

A slider dim with no entry in ``ranges`` is given an ``AutoRangeContinuous`` of ``(0, size, 1)``, and a
warning is raised. The reference value is then the array index itself, which is correct only when the units
of that dim really are indices.

The display window
------------------

For positional data the datapoints dim :math:`p` is both rendered and navigable, so it is not indexed at a
single value. For :math:`p` we define a **display window** :math:`w`, in the reference units of that
dimension and centered on the current index, which defines a window of datapoints that are rendered

.. math::

    W(\Lambda_p, w) = \left[\,\Phi_p(\Lambda_p - w/2),\ \ \Phi_p(\Lambda_p + w/2)\,\right)

taken with a step

.. math::

    \sigma = \max\left(1,\ \left\lfloor \frac{|W|}{m} \right\rfloor\right)

where :math:`m` is ``max_display_datapoints``. The rendered slice of a positional array is therefore

.. math::

    S_A(\Lambda) = A\left[\lambda_1, \ldots, \lambda_n,\ :,\ W(\Lambda_p, w)\!:\!\sigma,\ :\right] \in
    \mathbb{R}^{\ell \times p' \times d}

with :math:`p' \leq m` datapoints per graphical element.

This is a form of out-of-core rendering for timeseries data. Only :math:`S_A` is rendered and uploaded to
the GPU, so the array can be much larger than VRAM. The default slicer reads the full :math:`p` dim and
windows it in memory. To read only :math:`W` from a dataset that does not fit in RAM, implement ``get`` in
an ``NDSlicer`` subclass for that data source. ``display_window=None`` renders every datapoint of
:math:`p`, and ``display_window=0`` renders the single datapoint at :math:`\Lambda_p`.

``max_display_datapoints`` caps the cost of a wide window by decimating it, and defaults to 1000. Use a
large ``max_display_datapoints`` for things like scatter rasters where you want to see every point.

On an ``NDTimeseries``, ``x_range_mode`` couples the camera x-range to the display window:

* ``None``: the camera is left alone
* ``"fixed"``: the camera x-range is set from :math:`w`, centered on :math:`\Lambda_p`, on every update
* ``"auto"``: as ``"fixed"``, and the camera x-range is also read on every render, so panning or zooming
  sets :math:`w` to the new width and :math:`\Lambda_p` to the new center

Window functions
----------------

For any slider dim we define a **window function** :math:`\omega` that aggregates or transforms the data
within a window around the current index

.. math::

    \omega : \mathbb{R}^{w} \to \mathbb{R}

Note that this window is different from the display window. It is declared as ``window_funcs``, a mapping of
a dim name onto a ``(func, window_size)`` pair where ``window_size`` is in the reference units of that dim.
The dim is sliced over

.. math::

    \left[\,\Phi_j(\Lambda_j - w_j/2),\ \ \Phi_j(\Lambda_j + w_j/2)\,\right)

and then reduced by :math:`\omega_j`. The upper bound is exclusive and clamped into
:math:`[0, \text{size}]`, so a window at either end of the range still reaches the first and last elements
and always covers at least one of them. A rolling average, a rolling median, a maximum projection and a
Gaussian smoothing are all of this form::

    window_funcs={"time": (np.mean, 2.5)},   # average over 2.5 seconds around the current index
    window_order=("time",),

``window_order`` is the order in which the functions are applied. If a dim has a window function defined but
it is not included in ``window_order``, the window function is ignored and the dim is indexed at a single
value.

:math:`\omega` is applied with ``axis`` and ``keepdims=True``, so the dim that it was applied to reduces to
size 1 and survives until every window function has run. This is why a window function must accept ``axis``
and ``keepdims``, and must not drop the dimension.

``datapoints_window_func`` is the equivalent for the datapoints dim of positional data, and is applied along
:math:`p` after the display window has been taken. It is a ``(func, apply_dims, window_size)`` tuple.
``func`` is given a sliding window view and reduces along the window axis, and ``apply_dims`` names the
coordinates of the value dim that it applies to, one of ``"all", "x", "y", "z", "xy", "xz", "yz", "xyz"``,
with the rest passed through unchanged.

``spatial_func`` is applied to the data slice after the window functions, just before it is rendered, such
as a spatial gaussian filter. It is given the slice in ``display_dims`` order, i.e. the array as it is
rendered, and must return an array with those same dims.

Graphic features
----------------

Colors, colormaps, and other features can also be mapped onto NDGraphics. The colors, sizes, markers,
thickness and colormap transform of positional data are **graphic features**, and each one is either
**static** or **windowed** based on the value that is passed.

A static feature does not change w.r.t. the current reference indices. It is a single value shared by every
graphical element, one value per element, or an iterator of per-element values such as
``itertools.cycle(["jet", "viridis"])``. ``cmap`` and ``thickness`` are always static.

A windowed feature carries one value per rendered datapoint and is re-sliced whenever the data is. As an
array it must span the full ``p`` dim of the data, ``[l, p, n_values]``, where ``n_values`` is what that
feature needs, 4 for an RGBA color and 1 for a size. It is sliced with the same display window as the data.

A windowed feature can also be a callable that takes the data slice and the display window slice, and
returns the values for the rendered datapoints. Use it to derive a feature from the data itself or from
another signal, such as the tracking likelihood of each keypoint::

    def alpha_from_likelihood(data_slice, dw_slice):
        # data_slice is [l, p, d] for the rendered datapoints
        colors = keypoint_colors[:, None, :].repeat(data_slice.shape[1], axis=1)  # [l, p, 4]
        colors[:, :, -1] = likelihoods[:, dw_slice]
        return colors

    ndw["video"].add_nd_scatter(
        keypoints,
        ("kp", "time", "xy"),
        ("kp", "time", "xy"),
        colors=alpha_from_likelihood,
    )

``colors`` and ``cmap`` are mutually exclusive and setting one clears the other. ``cmap_transform`` holds
the values that the colormap colors are mapped from, and ``cmap_range`` is the ``(min, max)`` of that
transform mapped onto the colormap. A windowed ``cmap_transform`` array takes its range from its own minimum
and maximum over the full ``p`` dim, so a datapoint keeps its color as the window slides over it. A callable
has no knowable range and so requires an explicit ``cmap_range``.

A feature that the graphic type does not have is ignored, such as ``thickness`` on a scatter or ``markers``
on a line.

The objects
-----------

An ``NDWidget`` contains a figure, a shared reference index, and one ``NDGraphic`` per array, each with its
own slicer.

``NDWidget``
^^^^^^^^^^^^

Contains an ``ImguiFigure``, the ``ReferenceIndices`` that holds :math:`\Lambda`, and one ``NDWSubplot``
per subplot of that figure. ::

              sliders, play, step, a linear selector, ndw.indices = {...}
                                  │
                                  v
                     ┌─────────────────────────┐
                     │    ReferenceIndices     │  Λ, in reference units
                     │   {"time": 46.4, ...}   │  one range per slider dim
                     └────────────┬────────────┘
                                  │  Λ, to every NDGraphic that
                                  │  declares the dim that changed
            ┌─────────────────────┼─────────────────────┐
            v                     v                     v
      ┌───────────┐         ┌───────────┐         ┌───────────┐
      │ NDGraphic │         │ NDGraphic │         │ NDGraphic │
      └───────────┘         └───────────┘         └───────────┘
       NDWSubplot            NDWSubplot            NDWSubplot
       ndw["video"]          ndw["traces"]         ndw["raster"]
      └──────────────────── ImguiFigure ─────────────────────┘

Several widgets can share one ``ReferenceIndices``, which is how one set of sliders drives subplots in
separate windows. The first is given ``ranges`` and the rest are given ``indices``::

    ndw_main = fpl.NDWidget(ranges={"time": (0, 600, 1 / 30)}, names=["video", "traces"])
    ndw_ephys = fpl.NDWidget(indices=ndw_main.indices, names=["spikes"])

``ReferenceIndices``
^^^^^^^^^^^^^^^^^^^^

Holds :math:`\Lambda` and the range of each slider dim, and schedules the updates. When an index changes it
schedules a fetch on every ``NDGraphic`` that declares that dim, and no other graphic is touched. Slider
dims can also be added and removed while the widget is running with ``push_dims`` and ``pop_dims``.

Fetches are asynchronous and run on the render loop's scheduler, so a slow or lazy data object does not
freeze the canvas. Dragging a slider displays only the latest fetch and drops older ones that are still in
progress, which keeps the drag responsive on data that cannot be read at frame rate. Playback, the step
buttons, a linear selector and assignment to ``ndw.indices`` queue their requests per graphic instead, and
every one of them is rendered in order.

``NDWSubplot``
^^^^^^^^^^^^^^

One ``Subplot`` and the ``NDGraphic`` objects drawn on it, reached with ``ndw[row, col]`` or
``ndw["name"]``. This is where the ``add_nd_*`` methods are. Several ``NDGraphic`` objects can share a
subplot, which is how keypoints are drawn over a video. ::

      NDWSubplot                              ndw["video"]
      ├── Subplot                             ndw.figure["video"]
      │     camera, axes, tooltip, selectors, imgui windows
      └── NDGraphic list                      ndw["video"].nd_graphics
            ├── NDImage      "frame"          add_video(...)
            └── NDPositions  "keypoints"      add_nd_scatter(...)

``NDGraphic``
^^^^^^^^^^^^^

An n-dimensional graphical representation of data that is sliced by an ``NDSlicer``. It asks the slicer for
the slice at the current index and writes it into the graphic's buffers, allocating new buffers only when
the shape of the slice changes. ::

            Λ
            │
            v
      ┌─────────────────────────────────────────────────┐
      │ NDGraphic                                       │
      │   slicer.get(Λ)  ->  {"data": ..., <features>}  │
      │   write the result into the Graphic's buffers   │
      └───────────────────────┬─────────────────────────┘
                              v
                           Graphic     LineStack, ImageGraphic, ScatterCollection, ...

``ndg.graphic`` is the ``Graphic`` itself, so tooltips, event handlers, selectors and colormaps work on it
as they do anywhere else in fastplotlib.

``NDSlicer``
^^^^^^^^^^^^

Holds the data and turns :math:`\Lambda` into the slice to render. ::

   Λ = {"time": 46.397, "depth": 23.2}         reference units
        │
        │  Φ        slider_maps
        v
   array indices, clamped into [0, size - 1]
        │
        │  a window for each slider dim that has one, a single index for the rest
        v
   data[...]                                   the read from the data object
        │
        │  ω        window_funcs, in window_order
        v
   the windowed dims are size 1 and are squeezed out
        │
        │  W, σ     display window on p, positional data only,
        │           then datapoints_window_func
        v
   transposed to display order
        │
        │  spatial_func
        v
   the data slice

The data does not have to be an array. It has to behave as though the declared dims exist, and ``get`` has
to return a slice that the graphic can render, which is how a ``pandas.DataFrame`` or a ``spikeinterface``
recording is used as a data source.

The graphics and the slicers
----------------------------

+------------------+------------------------------+------------------+------------------------+-----------------------+
| ``NDGraphic``    | nd shape                     | NDSlicer output  | ``Graphic``            | added with            |
+==================+==============================+==================+========================+=======================+
| ``NDImage``      | ``[s_1, s_2, ..., r, c]``    | ``[r, c]``,      | ``ImageGraphic``,      | ``add_nd_image``,     |
|                  |                              | ``[r, c, v]``,   | ``ImageYUVGraphic``,   | ``add_video``         |
|                  |                              | ``[z, r, c]``    | ``ImageVolumeGraphic`` |                       |
+------------------+------------------------------+------------------+------------------------+-----------------------+
| ``NDPositions``  | ``[s_1, s_2, ..., l, p, d]`` | ``[l, p', d]``   | ``LineCollection``,    | ``add_nd_lines``,     |
|                  |                              |                  | ``LineStack``,         | ``add_nd_scatter``    |
|                  |                              |                  | ``ScatterCollection``, |                       |
|                  |                              |                  | ``ScatterStack``       |                       |
+------------------+------------------------------+------------------+------------------------+-----------------------+
| ``NDTimeseries`` | ``[s_1, s_2, ..., l, p, d]`` | ``[l, p', d]``   | the four above and     | ``add_nd_timeseries`` |
|                  |                              |                  | ``ImageGraphic``       |                       |
+------------------+------------------------------+------------------+------------------------+-----------------------+
| ``NDVectors``    | ``[s_1, s_2, ..., k, 2, d]`` | ``[k, 2, d]``    | ``VectorsGraphic``     | ``add_nd_vectors``    |
+------------------+------------------------------+------------------+------------------------+-----------------------+

``NDImage``
^^^^^^^^^^^

``display_dims`` determines the graphic. ``[rows, cols]`` is a grayscale ``ImageGraphic``,
``[rows, cols, rgb_dim]`` is an RGB(A) ``ImageGraphic``, ``[depth, rows, cols]`` is an
``ImageVolumeGraphic``, and a YUV ``colorspace`` is an ``ImageYUVGraphic``. Reassigning ``display_dims``
swaps the graphic when the number of rendered dims changes, so a volume can become a single plane while the
widget is running.

``compute_histogram=True``, the default, estimates a histogram of the data and puts an ``ImguiColorbar`` on
the edge of the subplot for setting vmin and vmax. ``clim_quantiles`` takes vmin and vmax from quantiles of
that histogram instead, and follows the data as the histogram is recomputed.

``NDPositions``
^^^^^^^^^^^^^^^

Four interchangeable representations of the same ``[l, p', d]`` slice. ``LineCollection`` and
``ScatterCollection`` draw the ``l`` graphical elements in one coordinate system, ``LineStack`` and
``ScatterStack`` separate them along y. ``graphic_type`` is mutable at runtime.

``NDTimeseries``
^^^^^^^^^^^^^^^^

``NDPositions`` for the case where ``p`` is a time-like x axis. It adds three things:

* ``ImageGraphic`` as a representation, which draws the slice as a heatmap of ``l`` rows where the color is
  the y coordinate and the x coordinates become the offset and scale of the image. This requires a value
  dim of exactly 2.
* a ``LinearSelector`` that marks :math:`\Lambda_p`. Dragging it sets that index, so it drives every
  graphic that declares the dim.
* ``x_range_mode``, which couples the camera x-range to the display window.

``fpl.utils.heatmap_to_positions(heatmap, xvals)`` converts an array shaped ``[n_rows, n_timepoints]`` into
the ``[n_rows, n_timepoints, 2]`` that these expect.

``NDVectors``
^^^^^^^^^^^^^

A ``VectorsGraphic`` of ``k`` vectors, the equivalent of a quiver plot, where the slice holds a position
and a direction for each vector.

Slicers
^^^^^^^

``NDImageSlicer``, ``NDPositionsSlicer`` and ``NDVectorsSlicer`` read anything that satisfies
``fpl.protocols.ArrayProtocol``, i.e. ``dtype``, ``ndim``, ``shape`` and ``__getitem__``. That covers numpy,
zarr, HDF5, torch and CUDA arrays, and lazy readers of your own. A reader that returns futures is awaited.

``VideoSlicer`` subclasses ``NDImageSlicer`` for video. It reads the frame at the current index directly
and does not apply window functions. ``add_video`` uses it with YUV defaults, which sends the YUV planes
straight to the GPU instead of converting each frame to RGB.

``PandasSlicer`` subclasses ``NDPositionsSlicer`` and reads the coordinates of each graphical element from
named columns of a ``pandas.DataFrame`` instead of from an array. It takes one ``(x_col, y_col)`` tuple per
element, which is the shape of pose tracking output, so ``l`` is the number of tuples and ``p`` is the
number of rows. It is reached through ``fpl.nds_extras.pandas.PandasSlicer``. Every module under
``fpl.nds_extras`` is named after the library that it requires and is imported when you access it, so
nothing there is imported along with fastplotlib.

To read from something else, subclass the slicer whose output the graphic expects and implement ``get``,
which receives :math:`\Lambda` and returns the slice. ``_get_dw_slice(indices)`` gives the display window
slice and ``_ref_index_to_array_index(dim, value)`` maps a single dim. Pass the subclass as
``slicer_type=`` to ``add_nd_image`` and ``add_video``, or as ``slicer=`` to the positional methods, with
extra arguments in ``slicer_kwargs``.
