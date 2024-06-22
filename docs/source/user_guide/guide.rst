The `fastplotlib` guide
=======================

Installation
------------

To install use pip:

.. code-block::

    pip install -U fastplotlib

or install the bleeding edge from Github:

.. code-block::

    pip install -U https://github.com/fastplotlib/fastplotlib/archive/main.zip


What is `fastplotlib`?
----------------------

`fastplotlib` is a cutting-edge plotting library built using the `pygfx <https://github.com/pygfx/pygfx>`_ rendering engine.
The lower-level details of the rendering process (i.e. defining a scene, camera, renderer, etc.) are abstracted away, allowing users to focus on their data.
The fundamental goal of `fastplotlib` is to provide a high-level, expressive API that promotes large-scale explorative scientific visualization. We want to
make it easy and intuitive to produce interactive visualizations that are as performant and vibrant as a modern video game :D


How to use `fastplotlib`
------------------------

Before giving a detailed overview of the library, here is a minimal example::

    import fastplotlib as fpl
    import imageio.v3 as iio

    fig = fpl.Figure()

    data = iio.imread("imageio:astronaut.png")

    image_graphic = fig[0, 0].add_image(data=data)

    fig.show()

    if __name__ == "__main__":
        fpl.run()

.. image:: _static/guide_hello_world.png


This is just a simple example of how the `fastplotlib` API works to create a plot, add some image data to the plot, and then visualize it.
However, we are just scratching the surface of what is possible with `fastplotlib`.
Next, let's take a look at the building blocks of `fastplotlib` and how they can be used to create more complex visualizations.

**Figure**

The starting point for creating any visualization in `fastplotlib` is a `Figure` object. This can be a single plot or a grid of subplots.
The `Figure` object houses and takes care of the underlying rendering components such as the camera, controller, renderer, and canvas.
Most users won't need to use these directly; however, the ability to directly interact with the rendering engine is still available if
needed.

By default, if no ``shape`` argument is provided when creating a `Figure`, there will be a single subplot. All subplots in a `Figure` can be accessed using
indexing (i.e. `fig_object[i ,j]`).

After defining a `Figure`, we can begin to add `Graphic` objects.

**Graphics**

A `Graphic` can be an image, a line, a scatter, a collection of lines, and more. All graphics can also be given a convenient ``name``. This allows graphics
to be easily accessed from figures::

    fig = fpl.Figure()

    data = iio.imread("imageio:astronaut.png")

    image_graphic = fig[0, 0].add_image(data=data, name="astronaut")

    fig.show()

    fig[0, 0]["astronaut"]
..

Graphics also have mutable properties that can be linked to events. Some of these properties, such as the `data` or `colors` of a line can even be indexed,
allowing for the creation of very powerful visualizations.

(1) Common properties

+--------------+--------------------------------------------------------------------------------------------------------------+
| Feature Name | Description                                                                                                  |
+==============+==============================================================================================================+
| name         | Graphic name                                                                                                 |
+--------------+--------------------------------------------------------------------------------------------------------------+
| offset       | Offset position of the graphic, [x, y, z]                                                                    |
+--------------+--------------------------------------------------------------------------------------------------------------+
| rotation     | Graphic rotation quaternion                                                                                  |
+--------------+--------------------------------------------------------------------------------------------------------------+
| visible      | Access or change the visibility                                                                              |
+--------------+--------------------------------------------------------------------------------------------------------------+
| deleted      | Used when a graphic is deleted, triggers events that can be useful to indicate this graphic has been deleted |
+--------------+--------------------------------------------------------------------------------------------------------------+

(2) Graphic-Specific properties

    (a) `ImageGraphic`

    +------------------------+------------------------------------+
    | Feature Name           | Description                        |
    +========================+====================================+
    | data                   | Underlying image data              |
    +------------------------+------------------------------------+
    | vmin                   | Lower contrast limit of an image   |
    +------------------------+------------------------------------+
    | vmax                   | Upper contrast limit of an image   |
    +------------------------+------------------------------------+
    | cmap                   | Colormap of an image               |
    +------------------------+------------------------------------+

    (b) `LineGraphic`, `LineCollection`, `LineStack`

    +--------------+--------------------------------+
    | Feature Name | Description                    |
    +==============+================================+
    | data         | underlying data of the line(s) |
    +--------------+--------------------------------+
    | colors       | colors of the line(s)          |
    +--------------+--------------------------------+
    | cmap         | colormap of the line(s)        |
    +--------------+--------------------------------+
    | thickness    | thickness of the line(s)       |
    +--------------+--------------------------------+

    (c) `ScatterGraphic`

    +--------------+---------------------------------------+
    | Feature Name | Description                           |
    +==============+=======================================+
    | data         | underlying data of the scatter points |
    +--------------+---------------------------------------+
    | colors       | colors of the scatter points          |
    +--------------+---------------------------------------+
    | cmap         | colormap of the scatter points        |
    +--------------+---------------------------------------+
    | sizes        | size of the scatter points            |
    +--------------+---------------------------------------+

    (d) `TextGraphic`

    +-------------------+---------------------------+
    | Feature Name      | Description               |
    +===================+===========================+
    | text              | data of the text          |
    +-------------------+---------------------------+
    | font_size         | size of the text          |
    +-------------------+---------------------------+
    | face_color        | color of the text face    |
    +-------------------+---------------------------+
    | outline_color     | color of the text outline |
    +-------------------+---------------------------+
    | outline_thickness | thickness of the text     |
    +-------------------+---------------------------+

Using our example from above: once we add a `Graphic` to the figure, we can then begin to change its properties. ::

    image_graphic.vmax = 150

.. image:: _static/hello_world_vmax.png

`Graphic` properties also support slicing and indexing. For example ::

    image_graphic.data[::8, :, :] = 1
    image_graphic.data[:, ::8, :] = 1

.. image:: _static/hello_world_data.png

Now we have the basics of creating a `Figure`, adding `Graphics` to a `Figure`, and working with `Graphic` properties to dynamically change or alter them.
Let's take a look at how we can define events to link `Graphics` and their properties together.

Events
------

All events inherit from the `pygfx.Event` class (add link)

events table: 

PYGFX_EVENTS = [
    "key_down",
    "key_up",
    "pointer_down",
    "pointer_move",
    "pointer_up",
    "pointer_enter",
    "pointer_leave",
    "click",
    "double_click",
    "wheel",
    "close",
    "resize",
]

adding events (2 methods)

attributes of all events (table)

Selectors
---------

A primary feature of `fastplotlib` is the ability to easily interact with your data. Two extremely helpful tools that can
be used in order to facilitate this process are a `LinearSelector` and `LinearRegionSelector`.

A `LinearSelector` is a horizontal or vertical line slider. This tool allows you to very easily select different points in your
data. Let's look at an example: ::

    import fastplotlib as fpl
    import numpy as np

    # generate data
    xs = np.linspace(-10, 10, 100)
    ys = np.sin(xs)
    sine = np.column_stack([xs, ys])

    fig = fpl.Figure()

    sine_graphic = fig[0, 0].add_line(data=sine, colors="w")

    # add a linear selector the sine wave
    selector = sine_graphic.add_linear_selector()

    fig[0, 0].auto_scale()

    fig.show(maintain_aspect=False)

.. image:: _static/guide_linear_selector.gif


A `LinearRegionSelector` is very similar to a `LinearSelector` but as opposed to selecting a singular point of
your data, you are able to select an entire region.

`ImageWidget`
-------------

Often times, developing UIs for interacting with multi-dimension image data can be tedious and repetitive.
In order to aid with common image and video visualization requirements the `ImageWidget` automatically generates sliders
to easily navigate through different dimensions of your data. Let's look at an example: ::

    import fastplotlib as fpl
    import imageio.v3 as iio

    movie = iio.imread("imageio:cockatoo.mp4")

    # convert RGB movie to grayscale
    gray_movie = np.dot(movie[..., :3], [0.299, 0.587, 0.114])

    iw_movie = ImageWidget(
    data=gray_movie,
    cmap="gray"
    )

    iw_movie.show()

.. image:: _static/guide_image_widget.gif

Animations
----------

An animation function is a user-defined function that gets called on every rendering cycle. Let's look at an example: ::

    import fastplotlib as fpl
    import numpy as np

    data = np.random.rand(512, 512)

    fig = fpl.Figure()

    fig[0,0].add_image(data=data, name="random-img")

    def update_data(plot_instance):
        new_data = np.random.rand(512, 512)
        plot_instance["random-img"].data = new_data

    fig[0,0].add_animations(update_data)

    fig.show()

.. image:: _static/guide_animation.gif

Here we are defining a function that updates the data of the `ImageGraphic` in the plot with new random data. When adding an animation function, the
user-defined function will receive a plot instance as an argument when it is called.

Spaces
------

There are several spaces to consider when using `fastplotlib`:

1) World Space

    World space is the 3D space in which objects live. World space has no limits on its size. Objects
    and the camera can exist anywhere in this space. Objects in this space exist relative to a larger
    world.

2) Data Space

    Data space is simply the world space plus any offset or rotation that has been applied to an object.

3) Screen Space

    Screen space is a 2D space represented in pixels. This space is constrained by the screen width and screen height.
    In the rendering process, the camera is responsible for projecting the world space into screen space.

.. note::
    When interacting with `Graphic` objects, there is a very helpful function for mapping screen space to world space
    (`Figure.map_screen_to_world(pos=(x, y))`). This can be particularly useful when working with click events where click
    positions are returned in screen space but `Graphic` objects that you may want to interact with exist in world
    space.


Using `fastplotlib` interactively
---------------------------------

There are multiple ways to use `fastplotlib` interactively.

On `jupyter lab` or `jupyter notebook` the jupyter backend (i.e. `jupyter_rfb`) is normally selected. This works via
client-server rendering. Images generated on the server are streamed to the client (Jupyter) via a jpeg byte stream.
Events (such as mouse or keyboard events) are then streamed in the opposite direction prompting new images to be generated
by the server if necessary. This remote-frame-buffer approach makes the rendering process very fast. `fastplotlib` viusalizations
can be displayed in cell output or on the side using `jupyterlab-sidecar`.

However, a Qt backend can optionally be used as well. If `%gui qt` is selected before importing `fastplotlib` then this backend
will be used instead.
Users can also force using `glfw` by specifying this as an argument when instantiating a `Figure` (i.e. `Figure(canvas="gflw"`).

.. note::
    Do not mix between gui backends. For example, if you start the notebook using Qt, do not attempt to force using another backend such
    as `jupyter_rfb` later.


Furthermore, in `IPython`, users can select between using a Qt backend or gflw the same as above.

