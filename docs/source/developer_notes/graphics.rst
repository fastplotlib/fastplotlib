Graphics
========


A ``Graphic`` is something that can be added to a ``PlotArea`` (described in detail in the layouts section). All the various
fastplotlib graphics, such as ``ImageGraphic``, ``ScatterGraphic``, etc. inherit from the ``Graphic`` base class in
``fastplotlib/graphics/_base.py``. It has a few properties that mostly wrap ``pygfx`` ``WorldObject`` properties and transforms.

Inheritance Diagram
-------------------

.. code-block:: rst

    Graphic
    │
    ├─ ImageGraphic
    │
    ├─ TextGraphic
    │
    ├─ PositionsGraphic
    │   │
    │   ├─ LineGraphic
    │   │
    │   └─ ScatterGraphic
    │
    └─ GraphicCollection
        │
        └─ LineCollection
            │
            └─ LineStack

..

All graphics can be given a string name for the user's convenience. This allows graphics to be easily accessed from
plots, ex: ``subplot["some_image"]``.

All graphics contain a ``world_object`` property which is just the ``pygfx.WorldObject`` that this graphic uses. Fastplotlib
keeps a *private* global dictionary of all ``WorldObject`` instances and users are only given a weakref proxy to this world object.
This is due to garbage collection. This may be quite complicated for beginners, for more details see this PR: https://github.com/fastplotlib/fastplotlib/pull/160 .
Furthermore, garbage collection is even more complicated in ipython and jupyter (see https://github.com/fastplotlib/fastplotlib/pull/546 ).
If you are curious or have more questions on garbage collection in ``fastplotlib`` you're welcome to post an issue :D.

Graphic collections are collections of graphics. For now, we have a ``LineCollection`` which is a collection of ``LineGraphic`` objects. We also have a ``LineStack`` which
inherits from ``LineCollection`` and gives some fixed offset between ``LineGraphic`` objects in the collection. A graphic collection behaves like an array of graphics.

Graphic Properties
------------------

Graphic properties are all evented, and internally we call these "graphic features". They are the various
aspects of a graphic that the user can change.
The "graphic features" subpackage can be found at ``fastplotlib/graphics/_features``. As we can see this
is a private subpackage and never meant to be accessible to users.

For example let's look at ``LineGraphic`` in ``fastplotlib/graphics/line.py``. Every graphic has a class variable called
``_features`` which is a set of all graphic properties that are evented. It has the following evented properties:
``"data", "colors", "cmap", "thickness"`` in addition to properties common to all graphics, such as ``"name", "offset", "rotation", and "visible"``

Now look at the constructor for the ``LineGraphic`` base class ``PositionsGraphic``, it first creates an instance of ``VertexPositions``.
This is a class that manages vertex positions buffer. For the user, it defines the line data, and provides additional useful functionality.
It defines the line, and provides additional useful functionality.
For example, every time that the ``data`` is changed, the new data will be marked for upload to the GPU before the next draw.
In addition, event handlers will be called if any event handlers are registered.

``VertexColors``behaves similarly, but it can perform additional parsing that can create the colors buffer from different
forms of user input. For example if a user runs: ``line_graphic.colors = "blue"``, then ``VertexColors.__setitem__()`` will
create a buffer that corresponds to what ``pygfx.Color`` thinks is "blue". Users can also take advantage of fancy indexing,
ex: ``line_graphics.colors[bool_array] = "red"`` :smile:

``LineGraphic`` also has a ``VertexCmap``, this manages the line ``VertexColors`` instance to parse colormaps, for example:
``line_graphic.cmap = "jet"`` or even ``line_graphic.cmap[50:] = "viridis"``.

``LineGraphic`` also has a ``thickness`` property which is pretty simple, and ``DeletedFeature`` which is useful if you need
callbacks to indicate that the graphic has been deleted (for example, removing references to a graphic from a legend).

Other graphics have properties that are relevant to them, for example ``ImageGraphic`` has ``cmap``, ``vmin``, ``vmax``,
properties unique to images.