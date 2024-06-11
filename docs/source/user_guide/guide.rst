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
The fundamental goal of `fastplotlib` is to provide a high-level, expressive API that promotes large-scale explorative scientific visualization.


How to use `fastplotlib`
------------------------

Before giving a detailed overview of the library, here is a minimal example::

    import fastplotlib as fpl
    import numpy as np

    fig = fpl.Figure()

    data = np.random.rand(512, 512)

    image_graphic = fig[0,0].add_image(data=data)

    fig.show()

    if __name__ == "__main__":
        fpl.run()

.. image:: /_static/guide_hello_world.png


This is just a simple example of how the `fastplotlib` API works to create a plot, add some image data to the plot, and then visualize it.
However, this is just scratching the surface of what we can do with `fastplotlib`.
Next, we will take a look at the building blocks of `fastplotlib` and how they can be used to create more complex visualizations.

**Figure**

The base of any visualization in `fastplotlib` is a `Figure` object. This can be a singular plot or a grid of subplots.
The `Figure` object houses and takes care of the underlying rendering components such as the camera, controller, renderer, and canvas.

After defining a `Figure`, we can begin to add `Graphic` objects.

**Graphics**

A `Graphic` can be an image, a line, a scatter, a collection of lines, and more. All graphics can be given a string name. This allows graphics
to be easily accessed from figures::

    fig = fpl.Figure()

    data = np.random.rand(512, 512)

    image_graphic = fig[0,0].add_image(data=data, name="random-img")

    fig.show()

    fig[0,0]["random-img"]
..

Graphics also have mutable, indexable properties that can be linked to events.

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

Using our example from above: once we add a `Graphic` to the figure, we can then begin to change its features. ::

    image_graphic.cmap = "viridis"

.. image:: /_static/guide_image_cmap.png

`GraphicFeatures` also support slicing and indexing. For example ::

    image_graphic.data[::15] = 1
    image_graphic.data[15::] = 1

.. image:: /_static/guide_image_slice.png

Now that we have the basics of creating a `Figure`, adding `Graphics` to the `Figure`, and working with `GraphicFeatures` to change or alter a `Graphic`.
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

`ImageWidget`
-------------

Animations
----------



