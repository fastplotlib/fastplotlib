Migrating from matplotlib
=========================

``fastplotlib`` and ``matplotlib`` are completely unrelated libraries with very different models. Fastplotlib uses the
GPU for realtime interactive visualization which requires a different implementation, object model, and user-API
to optimally leverage the underlying rendering engine.

A ``Figure`` is a live object on a canvas that is rendered continuously, and every ``Graphic`` in it stays mutable for
as long as it exists. You change a visualization by setting the properties of the graphic in a subplot. There
is nothing for you to redraw.

This is fundamentally different from making an animation in ``matplotlib``, where each frame comes from a callback
that clears the axes and plots the data again, or that returns the artists which have to be redrawn. There is no such
step here. The canvas redraws on every rendering cycle and any changed property values are automatically updated in the
visualization.

Use the intuition you have for creating and modifying ``numpy`` arrays, not the one you have for ``matplotlib``. Every
aspect of a ``Graphic`` is an array. Its ``data``, ``colors``, ``sizes``, ``thickness`` and the rest are indexed,
sliced, and assigned into the same way a numpy array is. Each assignment writes straight into the GPU buffer behind
that property.

.. note::
    Bringing ``matplotlib`` habits with you will also cost you performance. Modify the properties of the graphics that
    are already in the scene, do not create new ones. Creating a graphic allocates GPU buffers, and clearing a subplot
    to plot into it again throws those buffers away and uploads all of the data from scratch.

This page gives the ``fastplotlib`` equivalent of the ``matplotlib`` operations that come up most often. In the
examples below ``subplot`` is ``figure[0, 0]``.

Figures and subplots
--------------------

A ``Figure`` is created with a ``shape``, and each ``Subplot`` in it is accessed by index::

    import numpy as np
    import fastplotlib as fpl

    figure = fpl.Figure(shape=(2, 3), size=(900, 600))   # plt.subplots(2, 3)
    subplot = figure[0, 0]

    figure.show(maintain_aspect=False)                   # plt.show()

``size`` is the size of the canvas in pixels. Pass ``names`` to access a subplot by name, ``figure["temperature"]``.

Subplots created from a ``shape`` are laid out on a grid. To place them at arbitrary positions instead, pass one of:

* ``rects``, an ``(x, y, width, height)`` for each subplot
* ``extents``, an ``(xmin, xmax, ymin, ymax)`` for each subplot

Both are given either as fractions of the canvas or in absolute pixels.

There is no ``pyplot`` equivalent: no global state, no current figure, no current subplot, and no ``gca()``. You always
call a method on the object you want to affect, so a graphic is added with ``figure[0, 0].add_line(data)``.

How a ``Figure`` is displayed depends on where you are running it:

* **jupyterlab**: ``figure.show()`` must be the last line of a notebook cell, or be wrapped in
  ``IPython.display.display()``.
* **applications, scripts, and most other use-cases**: call ``fastplotlib.loop.run()`` after ``figure.show()`` to start
  the event loop. It blocks, so it is not used in jupyterlab or IPython.
* **an interactive Qt window from jupyterlab or IPython**: run ``%gui qt`` before importing ``fastplotlib``.

``maintain_aspect=False`` lets the x, y, and z scales change independently. Use it when the data in each dimension are
of a different magnitude, such as a timeseries, and for most large heatmaps. ``True`` is usually what you want for
images.

Drawing data
------------

Each type of ``Graphic`` has its own ``add_<graphic>()`` method on the ``Subplot``::

    subplot.add_line(ys)                                   # ax.plot(ys)
    subplot.add_line(np.column_stack([xs, ys]))            # ax.plot(xs, ys)
    subplot.add_line(xy, thickness=3, dash_pattern="--")   # ax.plot(..., lw=3, ls="--")
    subplot.add_scatter(xy, sizes=8, markers="^")          # ax.scatter(..., s=8, marker="^")
    subplot.add_image(img, cmap="gray", vmin=0, vmax=255)  # ax.imshow(...)
    subplot.add_image(values)                              # ax.pcolormesh(values)
    subplot.add_inf_line([2.5], axis="x")                  # ax.axvline(2.5)
    subplot.add_inf_line([0.0], axis="y")                  # ax.axhline(0.0)
    subplot.add_polygon(vertices)                          # ax.fill_between, ax.axvspan
    subplot.add_vectors(positions, directions)             # ax.quiver(...)
    subplot.add_surface(heights)                           # ax.plot_surface(...)
    subplot.add_mesh(positions, indices)                   # a Poly3DCollection
    subplot.add_text("stim", offset=(2.5, 1.0, 0))         # ax.text(2.5, 1.0, "stim")

Positional data is ``[n_points, 2]`` or ``[n_points, 3]``. ``add_line`` also accepts a 1D array of y-values, and
generates the x-values as an integer range.

Everything on the GPU is 32-bit. A ``float64`` array is cast to ``float32`` with a warning on every upload.

``vmin`` and ``vmax`` are in the image data's own units. They are estimated from a subsample of the data when they are
not provided. ``add_image`` draws row 0 at the top, like ``imshow``.

``thickness`` and ``sizes`` are in screen pixels, so they do not change as you zoom. Pass ``size_space="world"`` to
express them in data units instead.

The ``matplotlib`` style strings work here too:

* ``dash_pattern``: ``"-"``, ``"--"``, ``"-."``, ``":"``
* ``markers``: ``"o"``, ``"s"``, ``"D"``, ``"+"``, ``"x"``, ``"^"``, ``"<"``, ``">"``, ``"v"``, ``"*"``

Axis ranges, aspect and autoscale
---------------------------------

The range that a ``Subplot`` currently shows is read and set through ``x_range`` and ``y_range``::

    subplot.x_range = (0, 100)         # ax.set_xlim(0, 100)
    subplot.y_range = (-1, 1)          # ax.set_ylim(-1, 1)
    xmin, xmax = subplot.x_range       # ax.get_xlim()

    subplot.auto_scale(maintain_aspect=False, zoom=0.9)   # ax.autoscale()
    subplot.center_graphic(graphic)
    subplot.center_scene()

These two properties are in world space units, and they are only valid for an orthographic projection of the xy plane,
i.e. a camera with a field of view of 0. For a perspective projection, get and set the state of the camera directly::

    state = subplot.camera.get_state()
    subplot.camera.set_state({"position": (0, 0, 40), "fov": 50})

``subplot.camera.maintain_aspect = True`` keeps the x, y, and z scales locked to each other, which is what
``ax.set_aspect("equal")`` does.

An axis is inverted by flipping the scale of the camera, ``subplot.camera.local.scale_y = -1``. Subplots that contain
an image have this set at ``figure.show()``, which is why image row 0 is drawn at the top.

Title, axis labels, ticks and text
----------------------------------

The subplot title, the axis labels, and standalone text are set like this::

    subplot.title = "penguin data"                 # ax.set_title("penguin data")
    subplot.title.font_size = 20
    subplot.title.face_color = "r"

    subplot.axes.x.label.set_text("time (s)")      # ax.set_xlabel("time (s)")
    subplot.axes.y.label.set_text("amplitude")     # ax.set_ylabel("amplitude")

    subplot.add_text("stim", offset=(2.5, 1.0, 0), font_size=14, anchor="middle-left")

Text is drawn in screen space by default, so its size does not change as you zoom. Pass ``screen_space=False`` for text
that scales with the world instead. ``anchor`` is a vertical and a horizontal anchor separated by a dash, such as
``"top-left"`` or ``"middle-center"``.

Ticks are set on the ruler for each axis::

    subplot.axes.x.ticks = {0: "baseline", 30: "stim", 60: "recovery"}   # values and labels
    subplot.axes.x.ticks = [0, 30, 60]                                   # values, labels from format
    subplot.axes.x.ticks = None                                          # automatic ticks
    subplot.axes.y.tick_format = ".2f"       # a format spec, "km" for SI suffixes, or a callable
    subplot.axes.x.min_tick_distance = 100   # closest automatic ticks may get, in pixels
    subplot.axes.x.tick_size = 12

A ``tick_format`` callable is given ``(value, min_value, max_value)`` and returns a string.

The visibility and colors of the axes, the grids, and the subplot background are set directly on those objects::

    subplot.axes.visible = False           # ax.axis("off")
    subplot.axes.grids.visible = False     # ax.grid(False)
    subplot.axes.color = "gray"
    subplot.background_color = ["black"]   # ax.set_facecolor("black")

``background_color`` takes a sequence of 1, 2 or 4 colors:

* one color for a flat background
* two colors for (bottom, top)
* four colors for (bottom left, bottom right, top left, top right)

A bare string is unpacked one character at a time and raises, so pass ``["black"]`` and not ``"black"``.

Colors and colormaps
--------------------

A color is given as one of:

* a single letter, ``"r"``
* a named color, ``"cyan"``
* a hex string, ``"#ff0000"``
* an RGBA sequence, ``(1.0, 0.0, 0.0, 1.0)``

The ``matplotlib`` ``"C0"`` and ``"tab:blue"`` forms are not colors here and will raise.

Colormaps come from the `cmap <https://cmap-docs.readthedocs.io/en/stable/catalog/>`_ library, so every ``matplotlib``
colormap name works, along with many more. ``graphic.cmap`` returns a :class:`cmap.Colormap`, not the string you
passed.

There is no color cycle. Lines and scatters are white unless you pass ``colors``. To give several graphics different
colors, put them in one collection and set a colormap across it::

    stack = subplot.add_line_stack(np.stack(traces), separation=(0, 2, 0), cmap="tab10")

On a collection the colormap is spread across the graphics, so each line gets one color from it. Pass a list of
colormap names, ``cmap=["jet"] * n_lines``, to give every line its own colormap along its datapoints instead.

In ``matplotlib`` a line whose color varies along its length is a ``LineCollection`` of segments. In ``fastplotlib``
you can just set a colormap on a line, or set per-datapoint colors like any other array. ``cmap_transform`` holds the
per-datapoint values that the colors are looked up from::

    line = subplot.add_line(np.column_stack([xs, ys]), cmap="viridis", cmap_transform=speed)
    line.cmap_range = (0, 10)

``cmap_range`` is the ``(min, max)`` of ``cmap_transform`` mapped onto the colormap. It defaults to the range of
``cmap_transform``.

A qualitative colormap takes integer labels as its ``cmap_transform``, which is very useful for things like cluster
colors. You do not set a color per datapoint. You set a colormap and give an array that says which class each datapoint
belongs to::

    # tab10 has 10 colors, so a cmap_range of (0, 10) makes label k always get color k
    scatter = subplot.add_scatter(xy, cmap="tab10", cmap_transform=cluster_labels, cmap_range=(0, 10))

``cmap`` and ``colors`` are mutually exclusive. While a colormap is set ``graphic.colors`` is ``None``, and setting
``colors`` clears the colormap.

A single color is stored as one value rather than as a buffer, so it cannot be sliced. Per-datapoint colors are an
``[n_points, 4]`` RGBA array, and a graphic that has them is indexed and sliced like any other array::

    scatter = subplot.add_scatter(xy, colors="r")   # one color for every point, not sliceable

    scatter.colors = np.random.rand(n_points, 4)    # now one color per point
    scatter.colors[mask] = "w"

Passing the array to the constructor, ``add_scatter(xy, colors=np.random.rand(n_points, 4))``, initializes the graphic
with per-datapoint colors from the beginning.

.. note::
    Use a ``cmap`` with a ``cmap_transform`` instead of an RGBA array whenever you can. An RGBA array stores four
    float values for every datapoint, so it takes up far more GPU RAM than a colormap and a transform do.

Many graphics at once
---------------------

In ``matplotlib`` you would call ``ax.plot()`` in a loop to draw many lines. In ``fastplotlib`` you use a collection,
such as a ``LineCollection``, ``LineStack``, ``ScatterCollection``, ``ImageCollection``, or ``ImageGrid``. These are
created with ``add_line_collection``, ``add_line_stack``, ``add_scatter_collection``, ``add_scatter_stack``,
``add_image_collection``, and ``add_image_grid``.

Each property of the graphics it contains is exposed on the collection, and indexing that property indexes it across
the graphics::

    stack = subplot.add_line_stack(np.stack(traces), separation=(0, 2, 0), cmap="tab10")

    stack.colors[:10] = "r"            # the color of the first ten lines
    stack.thickness[mask] = 5
    stack.data[3, :, 1] = ys           # the y-values of the fourth line
    stack.visibles = False
    stack.graphics[3]                  # an individual graphic

The graphics in a collection can have different numbers of datapoints, so these properties are jagged. Fully
numpy-style fancy slicing is supported.

A property that the collection also has itself is exposed under a plural name. ``collection.offset`` is the offset of
the collection, and ``collection.offsets`` is the offset of each graphic in it.

Changing a plot after it is drawn
---------------------------------

You change a plot by setting mutable properties on graphics::

    line.data[:, 1] = new_ys          # line.set_ydata(new_ys)
    image.data[:] = frame             # im.set_data(frame)
    image.vmin, image.vmax = 0, 500   # im.set_clim(0, 500)
    scatter.sizes[mask] = 20
    graphic.visible = False
    subplot.delete_graphic(graphic)

A slice write uploads only the range that it touched. Assigning a whole array of a different length allocates a new GPU
buffer and re-uploads all of the data, so do that only when the number of datapoints has actually changed. Do not clear
a subplot and add the graphics again to refresh a plot.

An animation function is a user-defined function that gets called on every rendering cycle, and it receives the
subplot::

    def update(subplot):
        subplot["sine"].data[:, 1] = np.sin(xs + phase)

    figure[0, 0].add_animations(update)

``figure.add_animations(fn)`` calls ``fn`` with the figure instead. Do not drive an animation from a ``while`` loop, a
``time.sleep()``, or a thread.

Every graphic property emits an event when it changes, which you can use to drive other parts of a visualization::

    @image.add_event_handler("vmin", "vmax")
    def clim_changed(ev):
        print(ev.type, ev.info["value"])

``graphic.supported_events`` lists every event type that a graphic supports.

Pan, zoom and rotate
--------------------

A ``Figure`` is interactive and there is nothing to enable. There is no ``plt.ion()`` and no ``%matplotlib widget``,
and the same code is just as interactive in notebooks, Qt, glfw, and wx.

Every subplot has a camera and a controller, and you pan, zoom, and rotate with the mouse. If you do not pass a
``controller_type``, the controller is chosen from the field of view of the camera:

* **fov = 0**, an orthographic projection, gets a pan-zoom controller. Left drag pans, right drag zooms, and the wheel
  zooms toward the pointer.
* **fov > 0**, a perspective projection, gets a fly controller, which works like a first-person video game. ``wasd``
  moves, space and shift move up and down, ``q`` and ``e`` roll, left drag looks around, and the wheel changes the
  movement speed.

You can ask for a different controller, either for the whole figure or for one subplot::

    figure = fpl.Figure(controller_types="orbit")   # "panzoom", "orbit", "trackball", "fly"
    subplot.controller = "trackball"
    subplot.controller.enabled = False              # freeze the view

An orbit or trackball controller rotates around a center point with left drag, pans with right drag, and zooms with
the wheel.

``controller_types`` takes one value for the whole figure, or one value per subplot. Every subplot also has a toolbar
with autoscale, center, a controller toggle, and a maintain-aspect toggle, along with a right-click menu.

There is no Axes3D
------------------

There is no difference between 2D and 3D plotting in ``fastplotlib``, and there is nothing that corresponds to
``Axes3D``. Everything is always in 3D. Every subplot is a 3D scene and every graphic takes ``[n_points, 3]`` data.

The way a visualization looks depends entirely on the camera. A field of view of 0 is an orthographic projection, which
is what people commonly think of as a 2D plot. Any field of view above 0 is a perspective projection::

    figure = fpl.Figure(cameras="3d", controller_types="orbit")   # "3d" is a fov of 50
    subplot.camera.fov = 0                                        # orthographic projection
    subplot.add_line(np.column_stack([xs, ys, zs]))

A viewpoint is saved and restored through the state of the camera::

    state = subplot.camera.get_state()
    subplot.camera.set_state(state)

``get_state()`` returns ``position``, ``rotation``, ``scale``, ``reference_up``, ``fov``, ``width``, ``height``,
``depth``, ``zoom``, ``maintain_aspect``, and ``depth_range``. ``set_state()`` accepts any subset of those, along with
``x``, ``y``, and ``z`` to set a single component of the position.

Linked subplots
---------------

What ``sharex`` and ``sharey`` do in ``matplotlib`` is done here by sharing controllers between subplots.
``controller_ids`` links every subplot in the figure, or links them in groups::

    figure = fpl.Figure(shape=(2, 2), controller_ids="sync")   # every subplot linked

    figure = fpl.Figure(                                       # linked in groups
        shape=(1, 3),
        names=["temperature", "pressure", "map"],
        controller_ids=[("temperature", "pressure")],
    )

The camera and the controller are mutable properties on a ``Subplot``, just like most other properties in
``fastplotlib``. Set the controller of one subplot as the controller of another and the two of them share it, so they
pan and zoom together::

    figure["temperature"].controller = figure["pressure"].controller

To link a single axis, add the camera of the other subplot to a controller and say which part of the camera state to
share. This is what you want for stacked timeseries, where x pans and zooms together while each subplot keeps its own
y scale::

    figure[0, 0].controller.add_camera(figure[1, 0].camera, include_state={"x", "width"})
    figure[1, 0].controller.add_camera(figure[0, 0].camera, include_state={"x", "width"})

Colorbars
---------

A colorbar is an ``ImguiColorbar``, which you add to an edge of a subplot. It has draggable handles, a gamma slider,
and a right-click colormap picker, and it stays in sync with the graphic it controls::

    from fastplotlib.ui import ImguiColorbar

    image = figure[0, 0].add_image(data, cmap="viridis")
    figure[0, 0].add_imgui_window(ImguiColorbar(graphics=image), location="right", size=80)

Pass ``histogram=np.histogram(data, bins=100)`` to draw a histogram beside the bar. One colorbar can control several
graphics at once, ``ImguiColorbar(graphics=[image1, image2])``.

It works on a line or a scatter too, where the handles drive ``cmap_range``, the (min, max) of the
``cmap_transform`` that is mapped onto the colormap::

    line = figure[0, 0].add_line(data, cmap="viridis", cmap_transform=values)
    figure[0, 0].add_imgui_window(ImguiColorbar(graphics=line, title="depth"), location="right", size=80)

Defaults instead of rcParams
----------------------------

There is no ``rcParams`` and no ``style.use()``. Global defaults are set on the class that takes the argument, grouped
by the method they are passed to, so they tab-complete and a typo raises::

    fpl.LineGraphic.config.init.colors = "magenta"
    fpl.ImageGraphic.config.init.cmap = "gray"
    fpl.Figure.config.init.size = (900, 700)

A few preset styles are available in the ``fastplotlib.style`` namespace, and successive calls are merged::

    fpl.style.light()
    fpl.style.compact()

See :ref:`global_configuration` for every configurable component, and for how a config value interacts with an
argument that you pass explicitly.

There is no ``savefig``
-----------------------

Serializing a ``Figure`` is not supported yet. What you can do is explicitly export the canvas, exactly as it is on
screen, to a png::

    figure.export("plot.png")               # plt.savefig("plot.png")
    array = figure.export_numpy(rgb=True)

``export()`` goes through ``imageio``, so it writes any raster format that ``imageio`` supports. Vector formats such as
SVG are out of scope. ``fastplotlib`` is meant for live interactive visualization, not for creating publication figures
or videos.

Things with no direct equivalent
--------------------------------

* **Bar charts and stem plots** are out of scope.
* **Log-scaled axes** are not implemented yet. For now, plot the transformed values and set the tick labels
  explicitly, ``subplot.axes.x.ticks = {0: "1", 1: "10", 2: "100"}``.
* **Twin axes** are not implemented yet, they will come later as reference-spaces. For now, put the second signal in
  its own subplot and link the x range of the two controllers.
* **Contours.** Compute them with a library that does contouring and draw the result with ``add_line_collection``, or
  mark the regions on the image itself with an ``ImageHighlightSelector``.

The `examples gallery <https://www.fastplotlib.org/ver/dev/_gallery/index.html>`_ has runnable examples for every
graphic and for the things described on this page.
