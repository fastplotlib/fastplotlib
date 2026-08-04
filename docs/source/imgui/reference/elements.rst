Elements
========

The imgui elements as they exist in ``imgui_bundle``. Each element is shown with the code that produced its
image, which runs as it is written. See the :doc:`imgui guide </imgui/guide>` for adding a UI to a Figure.

An argument typed ``ImVec2`` or ``ImVec4`` also takes a tuple or a list.

The examples use ``imgui``, ``icons_fontawesome_6 as fa`` and ``numpy as np``.

Text
----

Text elements are read-only, they display a value that the user cannot edit.

text
^^^^

.. imgui-signature:: text

**Parameters**

* ``fmt`` - the text to draw

.. imgui-example::

    n_peaks = 137

    imgui.text(f"peaks found: {n_peaks}")

text_colored
^^^^^^^^^^^^

.. imgui-signature:: text_colored

**Parameters**

* ``col`` - text color, ``(r, g, b, a)`` in ``0.0`` to ``1.0``
* ``fmt`` - the text to draw

.. imgui-example::

    vmin, vmax = 180.0, 60.0

    if vmin > vmax:
        imgui.text_colored((1.0, 0.3, 0.3, 1.0), f"{fa.ICON_FA_TRIANGLE_EXCLAMATION} vmin > vmax")

text_disabled
^^^^^^^^^^^^^

.. imgui-signature:: text_disabled

**Parameters**

* ``fmt`` - the text to draw

.. imgui-example::

    selected = None

    imgui.text("selection:")
    imgui.same_line()

    if selected is None:
        imgui.text_disabled("none")
    else:
        imgui.text(selected)

text_wrapped
^^^^^^^^^^^^

.. imgui-signature:: text_wrapped

**Parameters**

* ``fmt`` - the text to draw, wrapped at the right edge of the window

.. imgui-example::
    :width: 220

    imgui.text_wrapped("the filter runs on the full frame, it can take a few seconds for large images")

label_text
^^^^^^^^^^

.. imgui-signature:: label_text

**Parameters**

* ``label`` - drawn to the right of the value, aligned the same way as the label of a slider or an input
* ``fmt`` - the value to draw

.. imgui-example::

    data = np.random.randint(0, 4096, (512, 512), dtype=np.uint16)

    imgui.label_text("shape", str(data.shape))
    imgui.label_text("dtype", str(data.dtype))
    imgui.label_text("range", f"{data.min()} - {data.max()}")

bullet_text
^^^^^^^^^^^

.. imgui-signature:: bullet_text

**Parameters**

* ``fmt`` - the text to draw after the bullet

.. imgui-example::

    imgui.text("controller:")
    imgui.bullet_text("left click drag to pan")
    imgui.bullet_text("right click drag to zoom")
    imgui.bullet_text("scroll to zoom about the cursor")

separator_text
^^^^^^^^^^^^^^

.. imgui-signature:: separator_text

**Parameters**

* ``label`` - the text to draw in the separator

.. imgui-example::

    thickness, sigma = 4.0, 1.0

    imgui.separator_text("line")
    changed, thickness = imgui.slider_float("thickness", v=thickness, v_min=1.0, v_max=20.0)

    imgui.separator_text("image")
    changed, sigma = imgui.slider_float("gaussian sigma", v=sigma, v_min=0.1, v_max=10.0)

Widgets
-------

button
^^^^^^

.. imgui-signature:: button

**Parameters**

* ``label`` - drawn on the button, ``"##hidden"`` suppresses it
* ``size`` - ``(width, height)``, a zero component is sized to the label, a negative one fills the available space

**Returns:** ``True`` on the frame the button is clicked

.. imgui-example::

    if imgui.button("autoscale"):
        print("autoscale clicked")

    if imgui.button(fa.ICON_FA_TRASH):
        print("trash clicked")
    if imgui.is_item_hovered():
        imgui.set_tooltip("remove all graphics")

small_button
^^^^^^^^^^^^

.. imgui-signature:: small_button

**Parameters**

* ``label`` - drawn on the button

**Returns:** ``True`` on the frame the button is clicked

.. imgui-example::

    vmin, vmax = 12.0, 208.0

    imgui.text(f"vmin {vmin:.0f}, vmax {vmax:.0f}")
    imgui.same_line()

    if imgui.small_button("reset"):
        vmin, vmax = 0.0, 255.0

arrow_button
^^^^^^^^^^^^

.. imgui-signature:: arrow_button

**Parameters**

* ``str_id`` - identifies the button, it is not drawn
* ``dir`` - ``imgui.Dir.left``, ``right``, ``up`` or ``down``

**Returns:** ``True`` on the frame the button is clicked

.. imgui-example::

    channel, n_channels = 1, 4

    if imgui.arrow_button("previous", imgui.Dir.left):
        channel = max(0, channel - 1)

    imgui.same_line()
    imgui.text(f"channel {channel}")

    imgui.same_line()
    if imgui.arrow_button("next", imgui.Dir.right):
        channel = min(n_channels - 1, channel + 1)

invisible_button
^^^^^^^^^^^^^^^^

.. imgui-signature:: invisible_button

**Parameters**

* ``str_id`` - identifies the button, nothing is drawn
* ``size`` - ``(width, height)`` of the area that responds to the pointer

**Returns:** ``True`` on the frame the button is clicked

An invisible button gives the pointer behavior of a button to an area that you draw yourself. The pointer is over the
button in the image below, so the bar is drawn in its highlighted color.

.. imgui-example::
    :interact: hover 40 20

    draw_list = imgui.get_window_draw_list()
    position = imgui.get_cursor_screen_pos()

    imgui.invisible_button("threshold-bar", (120, 24))

    color = (1.0, 0.8, 0.2, 1.0) if imgui.is_item_hovered() else (0.4, 0.4, 0.4, 1.0)
    draw_list.add_rect_filled(
        position, (position.x + 120, position.y + 24), imgui.color_convert_float4_to_u32(color)
    )

checkbox
^^^^^^^^

.. imgui-signature:: checkbox

**Parameters**

* ``label`` - drawn to the right of the box
* ``v`` - the current state

**Returns:** ``(changed, v)``

.. imgui-example::

    axes_visible, grid_visible = True, False

    changed, axes_visible = imgui.checkbox("axes", axes_visible)
    changed, grid_visible = imgui.checkbox("grid", grid_visible)

checkbox_flags
^^^^^^^^^^^^^^

.. imgui-signature:: checkbox_flags

**Parameters**

* ``label`` - drawn to the right of the box
* ``flags`` - the ``int`` that holds the bits
* ``flags_value`` - the bit that this checkbox sets and clears

**Returns:** ``(changed, flags)``

The box is checked when the bit is set, and is drawn filled when ``flags_value`` holds several bits and only some of
them are set.

.. imgui-example::

    slider_flags = int(imgui.SliderFlags_.logarithmic)

    changed, slider_flags = imgui.checkbox_flags(
        "logarithmic", slider_flags, int(imgui.SliderFlags_.logarithmic)
    )
    changed, slider_flags = imgui.checkbox_flags(
        "no input", slider_flags, int(imgui.SliderFlags_.no_input)
    )

radio_button
^^^^^^^^^^^^

.. imgui-signature:: radio_button

**Parameters**

* ``label`` - drawn to the right of the button
* ``active`` - whether this button is the selected one
* ``v``, ``v_button`` - the variable that holds the selection, and the value of this button

**Returns:** ``True`` on the frame the button is clicked, or ``(changed, v)`` for the second form

Use radio buttons for a small number of options that are all worth showing, a combo box is better for a long list.

.. imgui-example::

    mode = 1

    for i, label in enumerate(["line", "scatter", "heatmap"]):
        if imgui.radio_button(label, mode == i):
            mode = i

progress_bar
^^^^^^^^^^^^

.. imgui-signature:: progress_bar

**Parameters**

* ``fraction`` - ``0.0`` to ``1.0``
* ``size_arg`` - ``(width, height)``, the default fills the available width
* ``overlay`` - text drawn on the bar, the percentage is drawn if it is not given

.. imgui-example::
    :width: 280

    n_done, n_frames = 317, 500

    imgui.progress_bar(n_done / n_frames, overlay=f"{n_done} / {n_frames} frames")

bullet
^^^^^^

.. imgui-signature:: bullet

**Parameters**

none

.. imgui-example::

    shape = (500, 512, 512)

    imgui.bullet()
    imgui.text(f"{shape[0]} frames")

    imgui.bullet()
    imgui.text(f"{shape[1]} x {shape[2]} pixels")

Sliders
-------

A slider is dragged between a lower and an upper bound. A drag has no bound by default and changes its value by how
far the pointer moves, which suits a value with no natural range. Ctrl+click either of them to type a value instead.

``format`` is a printf format, it is applied to the value drawn on the element, e.g. ``"%.1f px"``.

slider_float
^^^^^^^^^^^^

.. imgui-signature:: slider_float

**Parameters**

* ``label`` - drawn to the right of the slider, ``"##hidden"`` suppresses it
* ``v`` - the current value
* ``v_min``, ``v_max`` - the bounds, the value is clamped to them
* ``format`` - printf format of the value drawn on the slider

**Returns:** ``(changed, v)``

.. imgui-example::

    thickness = 4.0

    changed, thickness = imgui.slider_float("thickness", v=thickness, v_min=1.0, v_max=20.0)

slider_float2
^^^^^^^^^^^^^

.. imgui-signature:: slider_float2

Two values on one row, sharing one pair of bounds. Pass a list and use the list that comes back.

**Parameters**

* ``label`` - drawn to the right of the sliders
* ``v`` - the current values
* ``v_min``, ``v_max`` - the bounds, applied to both components
* ``format`` - printf format of the values drawn on the sliders

**Returns:** ``(changed, v)``

.. imgui-example::

    vmin_vmax = [12.0, 208.0]

    changed, vmin_vmax = imgui.slider_float2("vmin / vmax", vmin_vmax, 0.0, 255.0, format="%.0f")

slider_float3
^^^^^^^^^^^^^

.. imgui-signature:: slider_float3

**Parameters**

* ``label`` - drawn to the right of the sliders
* ``v`` - the current values
* ``v_min``, ``v_max`` - the bounds, applied to every component
* ``format`` - printf format of the values drawn on the sliders

**Returns:** ``(changed, v)``

.. imgui-example::

    spacing = [1.0, 1.0, 3.0]

    changed, spacing = imgui.slider_float3("voxel spacing", spacing, 0.1, 10.0, format="%.2f")

slider_float4
^^^^^^^^^^^^^

.. imgui-signature:: slider_float4

**Parameters**

* ``label`` - drawn to the right of the sliders
* ``v`` - the current values
* ``v_min``, ``v_max`` - the bounds, applied to every component
* ``format`` - printf format of the values drawn on the sliders

**Returns:** ``(changed, v)``

.. imgui-example::

    extent = [0.1, 0.9, 0.1, 0.9]

    changed, extent = imgui.slider_float4("extent", extent, 0.0, 1.0, format="%.2f")

slider_int
^^^^^^^^^^

.. imgui-signature:: slider_int

**Parameters**

* ``label`` - drawn to the right of the slider
* ``v`` - the current value
* ``v_min``, ``v_max`` - the bounds, the value is clamped to them
* ``format`` - printf format of the value drawn on the slider

**Returns:** ``(changed, v)``

.. imgui-example::

    n_bins = 100

    changed, n_bins = imgui.slider_int("bins", v=n_bins, v_min=10, v_max=500)

slider_int2
^^^^^^^^^^^

.. imgui-signature:: slider_int2

**Parameters**

* ``label`` - drawn to the right of the sliders
* ``v`` - the current values
* ``v_min``, ``v_max`` - the bounds, applied to both components
* ``format`` - printf format of the values drawn on the sliders

**Returns:** ``(changed, v)``

.. imgui-example::

    crop = [64, 448]

    changed, crop = imgui.slider_int2("crop rows", crop, 0, 512)

slider_int3
^^^^^^^^^^^

.. imgui-signature:: slider_int3

**Parameters**

* ``label`` - drawn to the right of the sliders
* ``v`` - the current values
* ``v_min``, ``v_max`` - the bounds, applied to every component
* ``format`` - printf format of the values drawn on the sliders

**Returns:** ``(changed, v)``

.. imgui-example::

    stride = [1, 2, 2]

    changed, stride = imgui.slider_int3("stride", stride, 1, 8)

slider_int4
^^^^^^^^^^^

.. imgui-signature:: slider_int4

**Parameters**

* ``label`` - drawn to the right of the sliders
* ``v`` - the current values
* ``v_min``, ``v_max`` - the bounds, applied to every component
* ``format`` - printf format of the values drawn on the sliders

**Returns:** ``(changed, v)``

.. imgui-example::

    roi = [64, 64, 256, 256]

    changed, roi = imgui.slider_int4("roi", roi, 0, 512)

slider_angle
^^^^^^^^^^^^

.. imgui-signature:: slider_angle

The value is in radians, the bounds and the value drawn on the slider are in degrees.

**Parameters**

* ``label`` - drawn to the right of the slider
* ``v_rad`` - the current angle, in radians
* ``v_degrees_min``, ``v_degrees_max`` - the bounds, in degrees
* ``format`` - printf format of the angle drawn on the slider

**Returns:** ``(changed, v_rad)``

.. imgui-example::

    rotation = 0.6

    changed, rotation = imgui.slider_angle("rotation", v_rad=rotation, v_degrees_min=-180, v_degrees_max=180)

drag_float
^^^^^^^^^^

.. imgui-signature:: drag_float

**Parameters**

* ``label`` - drawn to the right of the element
* ``v`` - the current value
* ``v_speed`` - how much the value changes per pixel of pointer movement
* ``v_min``, ``v_max`` - the bounds, there is no bound while ``v_min >= v_max``
* ``format`` - printf format of the value drawn on the element

**Returns:** ``(changed, v)``

.. imgui-example::

    sigma = 1.4

    changed, sigma = imgui.drag_float("gaussian sigma", v=sigma, v_speed=0.05, v_min=0.1, v_max=20.0)

drag_float2
^^^^^^^^^^^

.. imgui-signature:: drag_float2

**Parameters**

* ``label`` - drawn to the right of the elements
* ``v`` - the current values
* ``v_speed`` - how much a value changes per pixel of pointer movement
* ``v_min``, ``v_max`` - the bounds, applied to both components, there is no bound while ``v_min >= v_max``
* ``format`` - printf format of the values drawn on the elements

**Returns:** ``(changed, v)``

.. imgui-example::

    origin = [0.0, 0.0]

    changed, origin = imgui.drag_float2("origin", origin, v_speed=0.5)

drag_float3
^^^^^^^^^^^

.. imgui-signature:: drag_float3

**Parameters**

* ``label`` - drawn to the right of the elements
* ``v`` - the current values
* ``v_speed`` - how much a value changes per pixel of pointer movement
* ``v_min``, ``v_max`` - the bounds, applied to every component, there is no bound while ``v_min >= v_max``
* ``format`` - printf format of the values drawn on the elements

**Returns:** ``(changed, v)``

.. imgui-example::

    offset = [0.0, 0.0, 0.0]

    changed, offset = imgui.drag_float3("offset", offset, v_speed=0.5)

drag_float4
^^^^^^^^^^^

.. imgui-signature:: drag_float4

**Parameters**

* ``label`` - drawn to the right of the elements
* ``v`` - the current values
* ``v_speed`` - how much a value changes per pixel of pointer movement
* ``v_min``, ``v_max`` - the bounds, applied to every component, there is no bound while ``v_min >= v_max``
* ``format`` - printf format of the values drawn on the elements

**Returns:** ``(changed, v)``

.. imgui-example::

    bounds = [0.0, 512.0, 0.0, 512.0]

    changed, bounds = imgui.drag_float4("bounds", bounds, v_speed=1.0, format="%.0f")

drag_float_range2
^^^^^^^^^^^^^^^^^

.. imgui-signature:: drag_float_range2

Two values that cannot cross, the lower one is dragged from the left half and the upper one from the right half.

**Parameters**

* ``label`` - drawn to the right of the element
* ``v_current_min``, ``v_current_max`` - the current values
* ``v_speed`` - how much a value changes per pixel of pointer movement
* ``v_min``, ``v_max`` - the bounds, there is no bound while ``v_min >= v_max``
* ``format`` - printf format of the lower value
* ``format_max`` - printf format of the upper value, ``format`` is used for both if it is not given

**Returns:** ``(changed, v_current_min, v_current_max)``

.. imgui-example::

    vmin, vmax = 12.0, 208.0

    changed, vmin, vmax = imgui.drag_float_range2(
        "vmin / vmax", vmin, vmax, v_speed=1.0, v_min=0.0, v_max=255.0, format="%.0f"
    )

drag_int
^^^^^^^^

.. imgui-signature:: drag_int

**Parameters**

* ``label`` - drawn to the right of the element
* ``v`` - the current value
* ``v_speed`` - how much the value changes per pixel of pointer movement
* ``v_min``, ``v_max`` - the bounds, there is no bound while ``v_min >= v_max``
* ``format`` - printf format of the value drawn on the element

**Returns:** ``(changed, v)``

.. imgui-example::

    window = 30

    changed, window = imgui.drag_int("window size", v=window, v_speed=1.0, v_min=1, v_max=500)

drag_int_range2
^^^^^^^^^^^^^^^

.. imgui-signature:: drag_int_range2

**Parameters**

* ``label`` - drawn to the right of the element
* ``v_current_min``, ``v_current_max`` - the current values, they cannot cross
* ``v_speed`` - how much a value changes per pixel of pointer movement
* ``v_min``, ``v_max`` - the bounds, there is no bound while ``v_min >= v_max``
* ``format`` - printf format of the lower value
* ``format_max`` - printf format of the upper value, ``format`` is used for both if it is not given

**Returns:** ``(changed, v_current_min, v_current_max)``

.. imgui-example::

    first, last = 40, 260

    changed, first, last = imgui.drag_int_range2("frames", first, last, v_min=0, v_max=500)

Input
-----

Input elements are typed into. A slider or a drag is better for a value that is explored by eye, an input is better
for a value that is known.

input_text
^^^^^^^^^^

.. imgui-signature:: input_text

**Parameters**

* ``label`` - drawn to the right of the field, ``"##hidden"`` suppresses it
* ``str`` - the current text
* ``callback``, ``user_data`` - an imgui input callback, for completion or filtering

**Returns:** ``(changed, str)`` - ``changed`` is ``True`` on every keystroke unless
:ref:`imgui.InputTextFlags_ <imgui.InputTextFlags_>` asks otherwise

.. imgui-example::
    :interact: click 60 18; type "a"

    name = "roi-1"

    changed, name = imgui.input_text("graphic name", name)

input_text_multiline
^^^^^^^^^^^^^^^^^^^^

.. imgui-signature:: input_text_multiline

**Parameters**

* ``label`` - drawn to the right of the field
* ``str`` - the current text
* ``size`` - ``(width, height)`` of the field, a zero component is a default size
* ``callback``, ``user_data`` - an imgui input callback

**Returns:** ``(changed, str)``

.. imgui-example::

    notes = "frame 42\nsaturated pixels\nrecheck vmax"

    changed, notes = imgui.input_text_multiline("notes", notes, (220, 70))

input_text_with_hint
^^^^^^^^^^^^^^^^^^^^

.. imgui-signature:: input_text_with_hint

The hint is drawn in the field while it is empty, use it instead of a label when there is no room for one.

**Parameters**

* ``label`` - drawn to the right of the field
* ``hint`` - drawn in the field while ``str`` is empty
* ``str`` - the current text
* ``callback``, ``user_data`` - an imgui input callback

**Returns:** ``(changed, str)``

.. imgui-example::

    pattern = ""

    changed, pattern = imgui.input_text_with_hint("##filter", "filter graphics", pattern)

input_float
^^^^^^^^^^^

.. imgui-signature:: input_float

**Parameters**

* ``label`` - drawn to the right of the field
* ``v`` - the current value
* ``step`` - amount the ``-`` and ``+`` buttons change the value by, they are not drawn while it is ``0.0``
* ``step_fast`` - amount used while ctrl is held
* ``format`` - printf format of the value in the field

**Returns:** ``(changed, v)``

.. imgui-example::

    threshold = 0.75

    changed, threshold = imgui.input_float("threshold", v=threshold, step=0.05, step_fast=0.5)

input_float2
^^^^^^^^^^^^

.. imgui-signature:: input_float2

Two, three, and four fields on one row. Pass a list and use the list that comes back.

**Parameters**

* ``label`` - drawn to the right of the fields
* ``v`` - the current values
* ``format`` - printf format of the values in the fields

**Returns:** ``(changed, v)``

.. imgui-example::

    pixel_size = [0.325, 0.325]

    changed, pixel_size = imgui.input_float2("pixel size (um)", pixel_size, format="%.3f")

input_float3
^^^^^^^^^^^^

.. imgui-signature:: input_float3

**Parameters**

* ``label`` - drawn to the right of the fields
* ``v`` - the current values
* ``format`` - printf format of the values in the fields

**Returns:** ``(changed, v)``

.. imgui-example::

    origin = [0.0, 0.0, 0.0]

    changed, origin = imgui.input_float3("origin", origin, format="%.1f")

input_float4
^^^^^^^^^^^^

.. imgui-signature:: input_float4

**Parameters**

* ``label`` - drawn to the right of the fields
* ``v`` - the current values
* ``format`` - printf format of the values in the fields

**Returns:** ``(changed, v)``

.. imgui-example::

    bounds = [0.0, 512.0, 0.0, 512.0]

    changed, bounds = imgui.input_float4("bounds", bounds, format="%.0f")

input_int
^^^^^^^^^

.. imgui-signature:: input_int

**Parameters**

* ``label`` - drawn to the right of the field
* ``v`` - the current value
* ``step`` - amount the ``-`` and ``+`` buttons change the value by
* ``step_fast`` - amount used while ctrl is held

**Returns:** ``(changed, v)``

.. imgui-example::

    n_components = 8

    changed, n_components = imgui.input_int("components", v=n_components, step=1, step_fast=10)

input_int2
^^^^^^^^^^

.. imgui-signature:: input_int2

**Parameters**

* ``label`` - drawn to the right of the fields
* ``v`` - the current values

**Returns:** ``(changed, v)``

.. imgui-example::

    shape = [512, 512]

    changed, shape = imgui.input_int2("output shape", shape)

input_int3
^^^^^^^^^^

.. imgui-signature:: input_int3

**Parameters**

* ``label`` - drawn to the right of the fields
* ``v`` - the current values

**Returns:** ``(changed, v)``

.. imgui-example::

    chunks = [1, 256, 256]

    changed, chunks = imgui.input_int3("chunks", chunks)

input_int4
^^^^^^^^^^

.. imgui-signature:: input_int4

**Parameters**

* ``label`` - drawn to the right of the fields
* ``v`` - the current values

**Returns:** ``(changed, v)``

.. imgui-example::

    roi = [64, 64, 256, 256]

    changed, roi = imgui.input_int4("roi", roi)

input_double
^^^^^^^^^^^^

.. imgui-signature:: input_double

**Parameters**

* ``label`` - drawn to the right of the field
* ``v`` - the current value
* ``step`` - amount the ``-`` and ``+`` buttons change the value by, they are not drawn while it is ``0.0``
* ``step_fast`` - amount used while ctrl is held
* ``format`` - printf format of the value in the field

**Returns:** ``(changed, v)``

.. imgui-example::
    :width: 260

    exposure = 0.008

    changed, exposure = imgui.input_double("exposure (s)", v=exposure, step=0.001, format="%.4f")

Selection
---------

combo
^^^^^

.. imgui-signature:: combo

**Parameters**

* ``label`` - drawn to the right of the box, ``"##hidden"`` suppresses it
* ``current_item`` - index of the selected item
* ``items`` - the items, as a sequence of strings
* ``popup_max_height_in_items`` - how many items the open list shows before it scrolls

**Returns:** ``(changed, current_item)``

.. imgui-example::

    mode, modes = 1, ["mip", "minip", "iso", "slice"]

    changed, mode = imgui.combo("render mode", mode, modes)

The list is drawn while the box is open:

.. imgui-example::
    :name: combo_open
    :interact: click 60 18

    mode, modes = 1, ["mip", "minip", "iso", "slice"]

    changed, mode = imgui.combo("render mode", mode, modes)

begin_combo
^^^^^^^^^^^

.. imgui-signature:: begin_combo

Use these instead of ``combo`` when the items are not plain strings, the body draws whatever it likes. Call
``end_combo`` only when ``begin_combo`` returned ``True``.

**Parameters**

* ``label`` - drawn to the right of the box
* ``preview_value`` - drawn in the box while it is closed

.. imgui-example::
    :name: begin_combo
    :interact: click 60 18

    selected, graphics = "line-1", ["line-1", "line-2", "scatter-1"]

    if imgui.begin_combo("graphic", selected):
        for name in graphics:
            clicked, _ = imgui.selectable(name, name == selected)
            if clicked:
                selected = name

        imgui.end_combo()

end_combo
^^^^^^^^^

.. imgui-signature:: end_combo

Call it only when the matching ``begin_combo`` returned ``True``.

**Parameters**

none

list_box
^^^^^^^^

.. imgui-signature:: list_box

A list box shows several items at once, a combo box hides them until it is opened.

**Parameters**

* ``label`` - drawn to the right of the box
* ``current_item`` - index of the selected item
* ``items`` - the items, as a sequence of strings
* ``height_in_items`` - how many items are visible before the box scrolls

**Returns:** ``(changed, current_item)``

.. imgui-example::

    selected, graphics = 0, ["line-1", "line-2", "scatter-1", "image-1"]

    changed, selected = imgui.list_box("graphics", selected, graphics, height_in_items=4)

begin_list_box
^^^^^^^^^^^^^^

.. imgui-signature:: begin_list_box

**Parameters**

* ``label`` - drawn to the right of the box
* ``size`` - ``(width, height)``, a zero component is a default size

.. imgui-example::
    :name: begin_list_box

    selected, graphics = "line-1", ["line-1", "line-2", "scatter-1"]

    if imgui.begin_list_box("graphics", (160, 70)):
        for name in graphics:
            clicked, _ = imgui.selectable(name, name == selected)
            if clicked:
                selected = name

        imgui.end_list_box()

end_list_box
^^^^^^^^^^^^

.. imgui-signature:: end_list_box

Call it only when the matching ``begin_list_box`` returned ``True``.

**Parameters**

none

selectable
^^^^^^^^^^

.. imgui-signature:: selectable

A row of text that can be selected, and the item to build lists out of.

**Parameters**

* ``label`` - drawn in the row
* ``p_selected`` - whether this row is drawn as selected
* ``size`` - ``(width, height)``, a zero component fills the available width

**Returns:** ``(clicked, p_selected)``

.. imgui-example::

    selected = "scatter-1"

    for name in ["line-1", "line-2", "scatter-1"]:
        clicked, _ = imgui.selectable(name, name == selected)
        if clicked:
            selected = name

Color
-----

A color is a list of floats in ``0.0`` to ``1.0``, three of them for RGB and four for RGBA. The ``3`` and ``4``
variants differ only in whether they include alpha.

color_edit3
^^^^^^^^^^^

.. imgui-signature:: color_edit3

A row of numeric fields with a color square at its right end. Clicking the square opens a picker, right-clicking it
opens a menu of display options.

**Parameters**

* ``label`` - drawn to the right of the fields, ``"##hidden"`` suppresses it
* ``col`` - the current color

**Returns:** ``(changed, col)``

.. imgui-example::

    color = [0.9, 0.3, 0.2]

    changed, color = imgui.color_edit3("line color", color)

color_edit4
^^^^^^^^^^^

.. imgui-signature:: color_edit4

``color_edit3`` with an alpha field.

**Parameters**

* ``label`` - drawn to the right of the fields
* ``col`` - the current color

**Returns:** ``(changed, col)``

.. imgui-example::

    color = [0.9, 0.3, 0.2, 0.5]

    changed, color = imgui.color_edit4("fill color", color)

color_picker3
^^^^^^^^^^^^^

.. imgui-signature:: color_picker3

The full picker, drawn inline. ``color_edit3`` is the compact element and opens this in a popup when its square is
clicked.

**Parameters**

* ``label`` - drawn above the picker
* ``col`` - the current color

**Returns:** ``(changed, col)``

.. imgui-example::

    color = [0.2, 0.6, 0.95]

    changed, color = imgui.color_picker3("##picker", color)

color_picker4
^^^^^^^^^^^^^

.. imgui-signature:: color_picker4

``color_picker3`` with an alpha bar.

**Parameters**

* ``label`` - drawn to the right of the picker
* ``col`` - the current color
* ``ref_col`` - a second color drawn beside the current one, to compare against

**Returns:** ``(changed, col)``

.. imgui-example::

    color = [0.2, 0.6, 0.95, 0.7]

    changed, color = imgui.color_picker4("##picker4", color)

color_button
^^^^^^^^^^^^

.. imgui-signature:: color_button

**Parameters**

* ``desc_id`` - identifies the button, and is shown in its tooltip
* ``col`` - the color to draw, ``(r, g, b, a)``
* ``size`` - ``(width, height)``, a zero component is a square the height of one row

**Returns:** ``True`` on the frame the button is clicked

.. imgui-example::

    for name, color in [("magenta", (1.0, 0.0, 1.0, 1.0)), ("cyan", (0.0, 1.0, 1.0, 1.0))]:
        if imgui.color_button(name, color, size=(40, 20)):
            print(f"{name} clicked")

        imgui.same_line()
        imgui.text(name)

set_color_edit_options
^^^^^^^^^^^^^^^^^^^^^^

.. imgui-signature:: set_color_edit_options

Sets the defaults for every color element that follows, so each one does not have to pass the same flags. Call it once
when the UI is created.

**Parameters**

* ``flags`` - the options to apply

.. imgui-example::

    imgui.set_color_edit_options(int(imgui.ColorEditFlags_.float) | int(imgui.ColorEditFlags_.display_hsv))

    color = [0.9, 0.3, 0.2]
    changed, color = imgui.color_edit3("line color", color)

Trees and tabs
--------------

tree_node
^^^^^^^^^

.. imgui-signature:: tree_node

Returns ``True`` while the node is open, in which case its contents are drawn and ``tree_pop`` must be called. The
node is opened and closed by the user, clicking the arrow.

**Parameters**

* ``label`` - drawn next to the arrow, and used as the id
* ``str_id``, ``ptr_id`` - an id given separately, for when the label is not unique or changes between frames
* ``fmt`` - the text to draw when an id is given separately

.. imgui-example::
    :interact: click 20 18

    if imgui.tree_node("image-1"):
        imgui.text("512 x 512, uint16")
        imgui.text("vmin 12, vmax 208")
        imgui.tree_pop()

tree_node_ex
^^^^^^^^^^^^

.. imgui-signature:: tree_node_ex

``tree_node`` with flags, e.g. to have the node start open, or to draw it without an arrow.

**Parameters**

* ``label`` - drawn next to the arrow, and used as the id
* ``str_id``, ``ptr_id`` - an id given separately
* ``fmt`` - the text to draw when an id is given separately

.. imgui-example::

    if imgui.tree_node_ex("image-1", flags=imgui.TreeNodeFlags_.default_open):
        imgui.text("512 x 512, uint16")
        imgui.tree_pop()

tree_pop
^^^^^^^^

.. imgui-signature:: tree_pop

**Parameters**

none

collapsing_header
^^^^^^^^^^^^^^^^^

.. imgui-signature:: collapsing_header

A header that shows and hides a section. Unlike a tree node it does not indent its contents and needs no
``tree_pop``, which makes it the element for grouping controls.

**Parameters**

* ``label`` - drawn in the header
* ``p_visible`` - when given, a close button is drawn and this is set to ``False`` when it is clicked

**Returns:** ``True`` while the header is open, or ``(open, p_visible)`` for the second form

.. imgui-example::

    sigma = 1.4

    if imgui.collapsing_header("filter", flags=imgui.TreeNodeFlags_.default_open):
        changed, sigma = imgui.slider_float("sigma", v=sigma, v_min=0.1, v_max=10.0)

    if imgui.collapsing_header("export"):
        imgui.text("not shown while the header is closed")

set_next_item_open
^^^^^^^^^^^^^^^^^^

.. imgui-signature:: set_next_item_open

Opens or closes the next tree node or collapsing header from code, rather than waiting for the user to click it.

**Parameters**

* ``is_open`` - the state to set
* ``cond`` - an ``imgui.Cond_`` value, e.g. ``once`` to set it only the first time

.. imgui-example::

    imgui.set_next_item_open(True, imgui.Cond_.once)

    if imgui.tree_node("image-1"):
        imgui.text("open because set_next_item_open was called")
        imgui.tree_pop()

begin_tab_bar
^^^^^^^^^^^^^

.. imgui-signature:: begin_tab_bar

**Parameters**

* ``str_id`` - identifies the tab bar, it is not drawn

.. imgui-example::
    :name: begin_tab_bar

    if imgui.begin_tab_bar("panels"):
        if imgui.begin_tab_item("image")[0]:
            imgui.text("512 x 512, uint16")
            imgui.end_tab_item()

        if imgui.begin_tab_item("filter")[0]:
            imgui.text("gaussian, sigma 1.4")
            imgui.end_tab_item()

        imgui.end_tab_bar()

end_tab_bar
^^^^^^^^^^^

.. imgui-signature:: end_tab_bar

Call it only when the matching ``begin_tab_bar`` returned ``True``.

**Parameters**

none

begin_tab_item
^^^^^^^^^^^^^^

.. imgui-signature:: begin_tab_item

**Parameters**

* ``label`` - drawn on the tab
* ``p_open`` - when given, a close button is drawn on the tab and this is set to ``False`` when it is clicked

**Returns:** ``(selected, p_open)``, draw the contents and call ``end_tab_item`` while ``selected``

.. imgui-example::
    :name: begin_tab_item
    :interact: click 90 22

    if imgui.begin_tab_bar("panels"):
        for label in ["image", "filter", "export"]:
            selected, _ = imgui.begin_tab_item(label)
            if selected:
                imgui.text(f"{label} panel")
                imgui.end_tab_item()

        imgui.end_tab_bar()

end_tab_item
^^^^^^^^^^^^

.. imgui-signature:: end_tab_item

Call it only when the matching ``begin_tab_item`` returned ``True``.

**Parameters**

none

tab_item_button
^^^^^^^^^^^^^^^

.. imgui-signature:: tab_item_button

**Parameters**

* ``label`` - drawn on the tab

**Returns:** ``True`` on the frame the tab is clicked

.. imgui-example::

    if imgui.begin_tab_bar("panels"):
        if imgui.begin_tab_item("image")[0]:
            imgui.end_tab_item()

        if imgui.tab_item_button("+"):
            print("add panel")

        imgui.end_tab_bar()

Menus
-----

A menu bar belongs to a window, so the window has to be created with ``imgui.WindowFlags_.menu_bar``.

begin_menu_bar
^^^^^^^^^^^^^^

.. imgui-signature:: begin_menu_bar

**Parameters**

none

.. imgui-example::
    :name: begin_menu_bar
    :window: none
    :interact: click 30 22

    imgui.set_next_window_pos((0, 0))
    imgui.set_next_window_size((220, 120))
    imgui.begin("controls", flags=imgui.WindowFlags_.menu_bar)

    if imgui.begin_menu_bar():
        if imgui.begin_menu("File"):
            imgui.menu_item("Open", "Ctrl+O", False)
            imgui.menu_item("Save", "Ctrl+S", False)
            imgui.end_menu()

        imgui.end_menu_bar()

    imgui.end()

end_menu_bar
^^^^^^^^^^^^

.. imgui-signature:: end_menu_bar

Call it only when the matching ``begin_menu_bar`` returned ``True``.

**Parameters**

none

begin_main_menu_bar
^^^^^^^^^^^^^^^^^^^

.. imgui-signature:: begin_main_menu_bar

A bar pinned across the top of the canvas, it is not part of any window.

**Parameters**

none

.. imgui-example::
    :name: begin_main_menu_bar
    :window: none
    :size: 260, 90
    :interact: click 60 10

    if imgui.begin_main_menu_bar():
        if imgui.begin_menu("File"):
            imgui.menu_item("Open", "Ctrl+O", False)
            imgui.end_menu()

        if imgui.begin_menu("Help"):
            imgui.menu_item("Version", "", False)
            imgui.end_menu()

        imgui.end_main_menu_bar()

end_main_menu_bar
^^^^^^^^^^^^^^^^^

.. imgui-signature:: end_main_menu_bar

Call it only when the matching ``begin_main_menu_bar`` returned ``True``.

**Parameters**

none

begin_menu
^^^^^^^^^^

.. imgui-signature:: begin_menu

Returns ``True`` while the menu is open, in which case its items are drawn and ``end_menu`` must be called. A
``begin_menu`` inside another one is a submenu.

**Parameters**

* ``label`` - drawn on the menu
* ``enabled`` - a disabled menu is drawn greyed out and cannot be opened

.. imgui-example::
    :name: begin_menu
    :window: none
    :size: 300, 140
    :interact: click 30 22; hover 45 66

    imgui.set_next_window_pos((0, 0))
    imgui.set_next_window_size((240, 130))
    imgui.begin("controls", flags=imgui.WindowFlags_.menu_bar)

    if imgui.begin_menu_bar():
        if imgui.begin_menu("Graphics"):
            imgui.menu_item("Add line", "", False)

            if imgui.begin_menu("Add image"):
                imgui.menu_item("from file", "", False)
                imgui.menu_item("from array", "", False)
                imgui.end_menu()

            imgui.end_menu()

        imgui.end_menu_bar()

    imgui.end()

end_menu
^^^^^^^^

.. imgui-signature:: end_menu

Call it only when the matching ``begin_menu`` returned ``True``.

**Parameters**

none

menu_item
^^^^^^^^^

.. imgui-signature:: menu_item

**Parameters**

* ``label`` - drawn on the item
* ``shortcut`` - drawn right-aligned on the item, it is a label only and does not bind the key
* ``p_selected`` - when ``True`` a check mark is drawn, pass it a bool to make the item a toggle
* ``enabled`` - a disabled item is drawn greyed out and cannot be clicked

**Returns:** ``(clicked, p_selected)``

.. imgui-example::
    :window: none
    :interact: click 30 22

    show_fps = True

    imgui.set_next_window_pos((0, 0))
    imgui.set_next_window_size((230, 120))
    imgui.begin("controls", flags=imgui.WindowFlags_.menu_bar)

    if imgui.begin_menu_bar():
        if imgui.begin_menu("View"):
            clicked, show_fps = imgui.menu_item("Show fps", "", show_fps)
            imgui.menu_item("Autoscale", "A", False)
            imgui.menu_item("Reset camera", "", False, enabled=False)
            imgui.end_menu()

        imgui.end_menu_bar()

    imgui.end()

Popups and tooltips
-------------------

A popup is opened by ``open_popup`` and drawn by ``begin_popup``, which returns ``True`` only while it is open. Both
have to be called for the same window, so calling ``open_popup`` from inside a menu does not open a popup that
``begin_popup`` draws outside of it.

open_popup
^^^^^^^^^^

.. imgui-signature:: open_popup

**Parameters**

* ``str_id`` - identifies the popup, ``begin_popup`` is called with the same id
* ``id_`` - an integer id instead of a string one
* ``popup_flags`` - options such as not opening over a popup that is already open

.. imgui-example::
    :interact: click 30 18

    if imgui.button("options"):
        imgui.open_popup("options")

    if imgui.begin_popup("options"):
        imgui.menu_item("reset vmin / vmax", "", False)
        imgui.menu_item("reset gamma", "", False)
        imgui.end_popup()

begin_popup
^^^^^^^^^^^

.. imgui-signature:: begin_popup

Call ``end_popup`` only when ``begin_popup`` returned ``True``. The popup closes when the user clicks outside it, or
when a menu item inside it is clicked.

**Parameters**

* ``str_id`` - the id that ``open_popup`` was called with

.. imgui-example::
    :name: begin_popup
    :interact: click 30 18

    sigma = 1.4

    if imgui.button("filter"):
        imgui.open_popup("filter")

    if imgui.begin_popup("filter"):
        changed, sigma = imgui.slider_float("sigma", v=sigma, v_min=0.1, v_max=10.0)
        imgui.end_popup()

end_popup
^^^^^^^^^

.. imgui-signature:: end_popup

Call it only when the matching ``begin_popup`` returned ``True``.

**Parameters**

none

begin_popup_modal
^^^^^^^^^^^^^^^^^

.. imgui-signature:: begin_popup_modal

A modal has a title bar and blocks everything behind it until it is closed. Passing ``p_open`` draws a close button in
its title bar.

**Parameters**

* ``name`` - the id that ``open_popup`` was called with, and the title
* ``p_open`` - when given, a close button is drawn and imgui closes the modal when it is clicked

**Returns:** ``(open, p_open)``

.. imgui-example::
    :interact: click 30 18

    if imgui.button("about"):
        imgui.open_popup("About")

    if imgui.begin_popup_modal("About", True)[0]:
        imgui.text("fastplotlib")
        imgui.end_popup()

close_current_popup
^^^^^^^^^^^^^^^^^^^

.. imgui-signature:: close_current_popup

Closes the popup being drawn, for a control that should dismiss it. A menu item already does this on its own.

**Parameters**

none

.. imgui-example::
    :interact: click 30 18

    if imgui.button("options"):
        imgui.open_popup("options")

    if imgui.begin_popup("options"):
        imgui.text("apply the filter to every frame?")

        if imgui.button("cancel"):
            imgui.close_current_popup()

        imgui.end_popup()

begin_popup_context_item
^^^^^^^^^^^^^^^^^^^^^^^^

.. imgui-signature:: begin_popup_context_item

Opens on a right-click on the element that precedes it, so a right-click menu needs no ``open_popup`` of its own.

**Parameters**

* ``str_id`` - identifies the popup, the preceding element is used when it is not given
* ``popup_flags`` - which mouse button opens it, right by default

.. imgui-example::
    :interact: right_click 40 18

    imgui.button("line-1")

    if imgui.begin_popup_context_item():
        imgui.menu_item("hide", "", False)
        imgui.menu_item("delete", "", False)
        imgui.end_popup()

begin_popup_context_window
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. imgui-signature:: begin_popup_context_window

Opens on a right-click anywhere in the window that is not over an element.

**Parameters**

* ``str_id`` - identifies the popup
* ``popup_flags`` - which mouse button opens it, right by default

.. imgui-example::
    :width: 180
    :interact: right_click 120 40

    imgui.text("right click the window")

    if imgui.begin_popup_context_window():
        imgui.menu_item("add line", "", False)
        imgui.menu_item("add image", "", False)
        imgui.end_popup()

is_popup_open
^^^^^^^^^^^^^

.. imgui-signature:: is_popup_open

**Parameters**

* ``str_id`` - the id the popup was opened with
* ``flags`` - use ``imgui.PopupFlags_.any_popup_id`` to ask about any popup

**Returns:** ``True`` while the popup is open

.. imgui-example::
    :interact: click 30 18

    if imgui.button("options"):
        imgui.open_popup("options")

    imgui.same_line()
    imgui.text(f"open: {imgui.is_popup_open('options')}")

    if imgui.begin_popup("options"):
        imgui.menu_item("reset", "", False)
        imgui.end_popup()

set_tooltip
^^^^^^^^^^^

.. imgui-signature:: set_tooltip

**Parameters**

* ``fmt`` - the text to draw in the tooltip

.. imgui-example::
    :interact: hover 30 18

    imgui.button(fa.ICON_FA_MAXIMIZE)

    if imgui.is_item_hovered():
        imgui.set_tooltip("autoscale scene")

set_item_tooltip
^^^^^^^^^^^^^^^^

.. imgui-signature:: set_item_tooltip

The same as ``set_tooltip`` behind an ``is_item_hovered`` check, for the common case of a tooltip on the element that
precedes it.

**Parameters**

* ``fmt`` - the text to draw in the tooltip

.. imgui-example::
    :interact: hover 30 18

    imgui.button(fa.ICON_FA_ALIGN_CENTER)
    imgui.set_item_tooltip("center scene")

begin_tooltip
^^^^^^^^^^^^^

.. imgui-signature:: begin_tooltip

A tooltip that holds any elements, not only text. Call ``end_tooltip`` only when ``begin_tooltip`` returned ``True``.

**Parameters**

none

.. imgui-example::
    :name: begin_tooltip
    :interact: hover 30 18

    imgui.button("image-1")

    if imgui.is_item_hovered() and imgui.begin_tooltip():
        imgui.text("image-1")
        imgui.separator()
        imgui.label_text("shape", "(512, 512)")
        imgui.label_text("dtype", "uint16")
        imgui.end_tooltip()

end_tooltip
^^^^^^^^^^^

.. imgui-signature:: end_tooltip

Call it only when the matching ``begin_tooltip`` returned ``True``.

**Parameters**

none

Layout
------

Elements are stacked vertically in the order they are called. These change where the next element goes, so most of them
draw nothing by themselves and are shown here between elements that do.

same_line
^^^^^^^^^

.. imgui-signature:: same_line

**Parameters**

* ``offset_from_start_x`` - x position in window coordinates, the default continues after the previous element
* ``spacing`` - gap in pixels, the default uses the style spacing

.. imgui-example::

    imgui.button("apply")
    imgui.same_line()
    imgui.button("reset")

new_line
^^^^^^^^

.. imgui-signature:: new_line

**Parameters**

none

.. imgui-example::

    imgui.button("apply")
    imgui.same_line()
    imgui.new_line()
    imgui.button("reset")

separator
^^^^^^^^^

.. imgui-signature:: separator

**Parameters**

none

.. imgui-example::

    imgui.text("filter")
    imgui.separator()
    imgui.text("export")

spacing
^^^^^^^

.. imgui-signature:: spacing

**Parameters**

none

.. imgui-example::

    imgui.button("apply")
    imgui.spacing()
    imgui.spacing()
    imgui.button("reset")

dummy
^^^^^

.. imgui-signature:: dummy

An empty element of a given size, to leave a gap that spacing cannot make. It takes no pointer input, unlike
``invisible_button``.

**Parameters**

* ``size`` - ``(width, height)`` of the gap

.. imgui-example::

    imgui.button("apply")
    imgui.same_line()
    imgui.dummy((40, 0))
    imgui.same_line()
    imgui.button("delete")

indent
^^^^^^

.. imgui-signature:: indent

**Parameters**

* ``indent_w`` - width in pixels, the default uses the style indent

.. imgui-example::
    :name: indent

    imgui.text("filter")
    imgui.indent()
    imgui.text("gaussian, sigma 1.4")
    imgui.text("applied to every frame")
    imgui.unindent()
    imgui.text("export")

unindent
^^^^^^^^

.. imgui-signature:: unindent

**Parameters**

* ``indent_w`` - width in pixels, the default uses the style indent

begin_group
^^^^^^^^^^^

.. imgui-signature:: begin_group

Everything between them becomes one item, so ``same_line`` places the whole group and ``is_item_hovered`` covers all of
it.

**Parameters**

none

.. imgui-example::
    :name: begin_group

    imgui.begin_group()
    imgui.text("vmin")
    imgui.text("12")
    imgui.end_group()

    imgui.same_line()
    imgui.dummy((20, 0))
    imgui.same_line()

    imgui.begin_group()
    imgui.text("vmax")
    imgui.text("208")
    imgui.end_group()

end_group
^^^^^^^^^

.. imgui-signature:: end_group

Ends the group, and makes everything in it one item for ``same_line`` and the item queries.

**Parameters**

none

align_text_to_frame_padding
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. imgui-signature:: align_text_to_frame_padding

Text is drawn without a frame, so on a row shared with a slider or a button it sits too high. Call this before the text
to line them up.

**Parameters**

none

.. imgui-example::

    sigma = 1.4

    imgui.align_text_to_frame_padding()
    imgui.text("sigma")
    imgui.same_line()
    changed, sigma = imgui.slider_float("##sigma", v=sigma, v_min=0.1, v_max=10.0)

set_next_item_width
^^^^^^^^^^^^^^^^^^^

.. imgui-signature:: set_next_item_width

**Parameters**

* ``item_width`` - width in pixels, a negative value leaves that many pixels between the element and the right edge

.. imgui-example::

    vmin, vmax = 12.0, 208.0

    imgui.set_next_item_width(80)
    changed, vmin = imgui.slider_float("vmin", v=vmin, v_min=0.0, v_max=255.0, format="%.0f")

    imgui.set_next_item_width(80)
    changed, vmax = imgui.slider_float("vmax", v=vmax, v_min=0.0, v_max=255.0, format="%.0f")

push_item_width
^^^^^^^^^^^^^^^

.. imgui-signature:: push_item_width

The same as ``set_next_item_width`` but for every element until ``pop_item_width``.

**Parameters**

* ``item_width`` - width in pixels, a negative value leaves that many pixels between the element and the right edge

.. imgui-example::
    :name: push_item_width

    vmin, vmax = 12.0, 208.0

    imgui.push_item_width(80)
    changed, vmin = imgui.slider_float("vmin", v=vmin, v_min=0.0, v_max=255.0, format="%.0f")
    changed, vmax = imgui.slider_float("vmax", v=vmax, v_min=0.0, v_max=255.0, format="%.0f")
    imgui.pop_item_width()

pop_item_width
^^^^^^^^^^^^^^

.. imgui-signature:: pop_item_width

Pops the width that ``push_item_width`` pushed.

**Parameters**

none

calc_text_size
^^^^^^^^^^^^^^

.. imgui-signature:: calc_text_size

**Parameters**

* ``text`` - the text to measure
* ``text_end`` - measure up to this substring
* ``hide_text_after_double_hash`` - ignore everything after ``##``, as the elements do with their labels
* ``wrap_width`` - measure as if the text were wrapped at this width

**Returns:** the size, use ``.x`` and ``.y``

.. imgui-example::

    label = "vmin / vmax"
    size = imgui.calc_text_size(label)

    imgui.text(label)
    imgui.text(f"that text is {size.x:.0f} x {size.y:.0f} px")

get_content_region_avail
^^^^^^^^^^^^^^^^^^^^^^^^

.. imgui-signature:: get_content_region_avail

The space left in the window from the current position, which is how an element is sized to fill the window.

**Parameters**

none

**Returns:** the available size, use ``.x`` and ``.y``

.. imgui-example::
    :width: 200

    available = imgui.get_content_region_avail()

    imgui.text(f"{available.x:.0f} x {available.y:.0f} px left")
    imgui.button("fill the width", (available.x, 0))

get_cursor_pos
^^^^^^^^^^^^^^

.. imgui-signature:: get_cursor_pos

Where the next element goes, in window coordinates.

**Parameters**

* ``local_pos`` - ``(x, y)`` in window coordinates

.. imgui-example::
    :name: set_cursor_pos

    imgui.set_cursor_pos((60, 30))
    imgui.button("moved")

set_cursor_pos
^^^^^^^^^^^^^^

.. imgui-signature:: set_cursor_pos

Moves the position of the next element, in window coordinates.

**Parameters**

* ``local_pos`` - ``(x, y)`` in window coordinates

.. imgui-example::

    imgui.set_cursor_pos((60, 30))
    imgui.button("moved")

get_cursor_screen_pos
^^^^^^^^^^^^^^^^^^^^^

.. imgui-signature:: get_cursor_screen_pos

The same position in canvas coordinates, which is what a draw list takes.

**Parameters**

* ``pos`` - ``(x, y)`` in canvas coordinates

.. imgui-example::
    :name: get_cursor_screen_pos

    draw_list = imgui.get_window_draw_list()
    position = imgui.get_cursor_screen_pos()

    draw_list.add_rect_filled(
        position,
        (position.x + 60, position.y + 20),
        imgui.color_convert_float4_to_u32((0.2, 0.6, 0.95, 1.0)),
    )
    imgui.dummy((60, 20))

set_cursor_screen_pos
^^^^^^^^^^^^^^^^^^^^^

.. imgui-signature:: set_cursor_screen_pos

Moves the position of the next element, in canvas coordinates.

**Parameters**

* ``pos`` - ``(x, y)`` in canvas coordinates

get_text_line_height
^^^^^^^^^^^^^^^^^^^^

.. imgui-signature:: get_text_line_height

The height of a line of text, and the height of an element that has a frame such as a button or a slider. Use them to
size something you draw yourself so that it lines up with the elements around it.

**Parameters**

none

.. imgui-example::
    :name: get_frame_height

    imgui.text(f"text line: {imgui.get_text_line_height():.0f} px")
    imgui.text(f"framed element: {imgui.get_frame_height():.0f} px")

get_frame_height
^^^^^^^^^^^^^^^^

.. imgui-signature:: get_frame_height

The height of an element that has a frame, such as a button or a slider.

**Parameters**

none

**Returns:** the height in pixels

.. imgui-example::

    imgui.text(f"framed element: {imgui.get_frame_height():.0f} px")

Windows
-------

In fastplotlib the window is created for you, ``ImguiWindow.update()`` draws into it. These are for a window you create
yourself, inside an overridden ``ImguiWindow.draw()``.

begin
^^^^^

.. imgui-signature:: begin

``end`` is called whether or not ``begin`` returned ``True``. ``begin`` returns ``False`` when the window is collapsed,
in which case its contents can be skipped.

**Parameters**

* ``name`` - the title, and the id of the window, ``"title##id"`` separates the two
* ``p_open`` - when given, a close button is drawn in the title bar and this is set to ``False`` when it is clicked

**Returns:** ``(expanded, p_open)``

.. imgui-example::
    :window: none
    :size: 240, 120

    expanded, open_ = imgui.begin("filter", True)

    if expanded:
        imgui.text("gaussian")

    imgui.end()

end
^^^

.. imgui-signature:: end

Called whether or not ``begin`` returned ``True``.

**Parameters**

none

begin_child
^^^^^^^^^^^

.. imgui-signature:: begin_child

A region within a window, with its own scrolling and clipping. Use it for a list that should scroll on its own.

**Parameters**

* ``str_id``, ``id_`` - identifies the region
* ``size`` - ``(width, height)``, a zero component fills the available space, a negative one leaves that many pixels

.. imgui-example::
    :name: begin_child

    if imgui.begin_child("graphics", (160, 80), child_flags=imgui.ChildFlags_.borders):
        for i in range(8):
            imgui.text(f"line-{i}")

        imgui.end_child()

end_child
^^^^^^^^^

.. imgui-signature:: end_child

Call it only when the matching ``begin_child`` returned ``True``.

**Parameters**

none

set_next_window_pos
^^^^^^^^^^^^^^^^^^^

.. imgui-signature:: set_next_window_pos

**Parameters**

* ``pos`` - ``(x, y)`` in canvas coordinates
* ``cond`` - an ``imgui.Cond_`` value, e.g. ``appearing`` to place it only when it first appears so the user can move it
* ``pivot`` - which point of the window lands on ``pos``, ``(0.5, 0.5)`` centers it there

.. imgui-example::
    :window: none
    :size: 260, 130

    imgui.set_next_window_pos((40, 30))
    imgui.set_next_window_size((160, 60))
    imgui.begin("filter")
    imgui.text("placed at 40, 30")
    imgui.end()

set_next_window_size
^^^^^^^^^^^^^^^^^^^^

.. imgui-signature:: set_next_window_size

**Parameters**

* ``size`` - ``(width, height)``, a zero component makes that axis fit its contents
* ``cond`` - an ``imgui.Cond_`` value

.. imgui-example::
    :window: none
    :size: 240, 120

    imgui.set_next_window_size((150, 0))
    imgui.begin("filter")
    imgui.text("fixed width, auto height")
    imgui.end()

set_next_window_collapsed
^^^^^^^^^^^^^^^^^^^^^^^^^

.. imgui-signature:: set_next_window_collapsed

**Parameters**

* ``collapsed`` - the state to set
* ``cond`` - an ``imgui.Cond_`` value

.. imgui-example::
    :window: none
    :size: 240, 90

    imgui.set_next_window_collapsed(True)
    imgui.begin("filter")
    imgui.text("not drawn while collapsed")
    imgui.end()

get_window_pos
^^^^^^^^^^^^^^

.. imgui-signature:: get_window_pos

The position and size of the window being drawn. For laying out contents, ``get_content_region_avail`` is what you
want, since it accounts for padding and for the position within the window.

**Parameters**

none

.. imgui-example::
    :name: get_window_size
    :width: 200

    size = imgui.get_window_size()

    imgui.text(f"window: {size.x:.0f} x {size.y:.0f} px")

get_window_size
^^^^^^^^^^^^^^^

.. imgui-signature:: get_window_size

**Parameters**

none

**Returns:** the size, use ``.x`` and ``.y``

.. imgui-example::
    :width: 200

    size = imgui.get_window_size()

    imgui.text(f"window: {size.x:.0f} x {size.y:.0f} px")

get_window_width
^^^^^^^^^^^^^^^^

.. imgui-signature:: get_window_width

**Parameters**

none

**Returns:** the width in pixels

get_window_height
^^^^^^^^^^^^^^^^^

.. imgui-signature:: get_window_height

**Parameters**

none

**Returns:** the height in pixels

get_window_draw_list
^^^^^^^^^^^^^^^^^^^^

.. imgui-signature:: get_window_draw_list

The draw list of the window, for drawing shapes and text yourself. Positions are in canvas coordinates, so they start
from ``get_cursor_screen_pos``.

**Parameters**

none

**Returns:** an ``imgui.ImDrawList``

.. imgui-example::

    draw_list = imgui.get_window_draw_list()
    position = imgui.get_cursor_screen_pos()

    white = imgui.color_convert_float4_to_u32((1.0, 1.0, 1.0, 1.0))
    blue = imgui.color_convert_float4_to_u32((0.2, 0.6, 0.95, 1.0))

    draw_list.add_rect_filled(position, (position.x + 120, position.y + 8), blue)
    draw_list.add_circle_filled((position.x + 30, position.y + 30), 8, white)
    draw_list.add_text((position.x + 50, position.y + 22), white, "drawn by hand")

    imgui.dummy((120, 45))

set_scroll_here_y
^^^^^^^^^^^^^^^^^

.. imgui-signature:: set_scroll_here_y

``set_scroll_here_y`` scrolls to the element that was just drawn, which is how a list follows a selection.

**Parameters**

* ``center_y_ratio`` - where the element ends up, ``0.0`` top, ``0.5`` center, ``1.0`` bottom
* ``scroll_y`` - the scroll amount in pixels

.. imgui-example::
    :name: set_scroll_here_y

    if imgui.begin_child("graphics", (160, 70), child_flags=imgui.ChildFlags_.borders):
        for i in range(10):
            imgui.text(f"line-{i}")

            if i == 6:
                imgui.set_scroll_here_y(0.5)

        imgui.end_child()

get_scroll_y
^^^^^^^^^^^^

.. imgui-signature:: get_scroll_y

**Parameters**

none

**Returns:** the scroll amount in pixels

set_scroll_y
^^^^^^^^^^^^

.. imgui-signature:: set_scroll_y

**Parameters**

* ``scroll_y`` - the scroll amount in pixels

Style and ids
-------------

Every push has a matching pop. A push that is not popped leaks into everything drawn afterwards, including elements
that fastplotlib draws.

push_id
^^^^^^^

.. imgui-signature:: push_id

imgui identifies an element by its label, so two elements with the same label are the same element and share their
state. Push an id around them to keep them apart, which is what a loop over graphics needs.

**Parameters**

* ``str_id``, ``int_id``, ``ptr_id`` - the value to push, it is hashed and is not drawn
* ``str_id_begin``, ``str_id_end`` - a substring to push

.. imgui-example::
    :name: push_id

    thickness = {"line-1": 4.0, "line-2": 9.0}

    for name in thickness:
        imgui.push_id(name)

        imgui.text(name)
        imgui.same_line()
        changed, thickness[name] = imgui.slider_float("##thickness", v=thickness[name], v_min=1.0, v_max=20.0)

        imgui.pop_id()

pop_id
^^^^^^

.. imgui-signature:: pop_id

Pops the id that ``push_id`` pushed.

**Parameters**

none

push_style_color
^^^^^^^^^^^^^^^^

.. imgui-signature:: push_style_color

**Parameters**

* ``idx`` - which color, an ``imgui.Col_`` value
* ``col`` - the color, ``(r, g, b, a)`` or a packed ``int``
* ``count`` - how many pushes to pop

.. imgui-example::
    :name: push_style_color

    imgui.push_style_color(imgui.Col_.button, (0.6, 0.15, 0.15, 1.0))
    imgui.push_style_color(imgui.Col_.button_hovered, (0.75, 0.2, 0.2, 1.0))

    imgui.button("delete graphic")

    imgui.pop_style_color(2)

    imgui.button("keep graphic")

pop_style_color
^^^^^^^^^^^^^^^

.. imgui-signature:: pop_style_color

**Parameters**

* ``count`` - how many pushed colors to pop

push_style_var
^^^^^^^^^^^^^^

.. imgui-signature:: push_style_var

**Parameters**

* ``idx`` - which variable, an ``imgui.StyleVar_`` value
* ``val`` - a float, or ``(x, y)`` for the variables that are a pair
* ``count`` - how many pushes to pop

.. imgui-example::
    :name: push_style_var

    imgui.push_style_var(imgui.StyleVar_.frame_rounding, 10.0)
    imgui.button("rounded")
    imgui.pop_style_var()

    imgui.button("default")

pop_style_var
^^^^^^^^^^^^^

.. imgui-signature:: pop_style_var

**Parameters**

* ``count`` - how many pushed variables to pop

get_style_color_vec4
^^^^^^^^^^^^^^^^^^^^

.. imgui-signature:: get_style_color_vec4

**Parameters**

* ``idx`` - which color, an ``imgui.Col_`` value

**Returns:** the color, use ``.x``, ``.y``, ``.z``, ``.w`` for r, g, b, a

.. imgui-example::

    color = imgui.get_style_color_vec4(imgui.Col_.text)

    imgui.text(f"text color: {color.x:.2f}, {color.y:.2f}, {color.z:.2f}")

get_color_u32
^^^^^^^^^^^^^

.. imgui-signature:: get_color_u32

A draw list takes a packed 32-bit color, not a tuple. ``get_color_u32`` packs a style color or your own color and
applies the global style alpha, ``color_convert_float4_to_u32`` packs a color as it is.

**Parameters**

* ``idx`` - which style color, an ``imgui.Col_`` value
* ``col`` - a color, ``(r, g, b, a)`` or a packed ``int``
* ``alpha_mul`` - multiplies the alpha
* ``in_`` - the color to pack, ``(r, g, b, a)``

**Returns:** the packed color

.. imgui-example::
    :name: get_color_u32

    draw_list = imgui.get_window_draw_list()
    position = imgui.get_cursor_screen_pos()

    draw_list.add_rect_filled(
        position, (position.x + 60, position.y + 20), imgui.get_color_u32(imgui.Col_.button)
    )
    draw_list.add_rect_filled(
        (position.x + 70, position.y),
        (position.x + 130, position.y + 20),
        imgui.color_convert_float4_to_u32((1.0, 0.8, 0.2, 1.0)),
    )

    imgui.dummy((130, 20))

color_convert_float4_to_u32
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. imgui-signature:: color_convert_float4_to_u32

Packs a color as it is, without applying the style alpha.

**Parameters**

* ``in_`` - the color to pack, ``(r, g, b, a)``

**Returns:** the packed color

get_font_size
^^^^^^^^^^^^^

.. imgui-signature:: get_font_size

**Parameters**

none

**Returns:** the height of the font in pixels

.. imgui-example::

    imgui.text(f"font size: {imgui.get_font_size():.0f} px")

begin_disabled
^^^^^^^^^^^^^^

.. imgui-signature:: begin_disabled

Everything between them is greyed out and takes no input, for a control that does not apply yet.

**Parameters**

* ``disabled`` - pass ``False`` to leave the elements enabled, so the call can be made unconditionally

.. imgui-example::
    :name: begin_disabled

    apply_filter, sigma = False, 1.4

    changed, apply_filter = imgui.checkbox("gaussian filter", apply_filter)

    imgui.begin_disabled(not apply_filter)
    changed, sigma = imgui.slider_float("sigma", v=sigma, v_min=0.1, v_max=10.0)
    imgui.end_disabled()

end_disabled
^^^^^^^^^^^^

.. imgui-signature:: end_disabled

Ends the block that ``begin_disabled`` started.

**Parameters**

none

Queries
-------

These ask about the element that was drawn last, about the window, or about the mouse and keyboard. The item queries
refer to the element immediately above them, so they go straight after the element they ask about.

The examples below print what they return, and the images were captured with the pointer over the element or a button
held down, which is why they read ``True``.

is_item_hovered
^^^^^^^^^^^^^^^

.. imgui-signature:: is_item_hovered

.. imgui-example::
    :interact: hover 30 18

    imgui.button("autoscale")
    imgui.text(f"hovered: {imgui.is_item_hovered()}")

is_item_active
^^^^^^^^^^^^^^

.. imgui-signature:: is_item_active

.. imgui-example::
    :interact: press 30 18

    imgui.button("autoscale")
    imgui.text(f"active: {imgui.is_item_active()}")

is_item_clicked
^^^^^^^^^^^^^^^

.. imgui-signature:: is_item_clicked

**Parameters**

* ``mouse_button`` - ``0`` left, ``1`` right, ``2`` middle

.. imgui-example::
    :interact: press 30 18

    imgui.button("autoscale")
    imgui.text(f"clicked: {imgui.is_item_clicked()}")

is_item_edited
^^^^^^^^^^^^^^

.. imgui-signature:: is_item_edited

``is_item_deactivated_after_edit`` is the one to use for work that is too expensive to run while a slider is being
dragged, since it is ``True`` only on the frame the drag ends.

.. imgui-example::
    :name: is_item_deactivated_after_edit
    :interact: drag 60 18 100 18

    sigma = 1.4

    changed, sigma = imgui.slider_float("sigma", v=sigma, v_min=0.1, v_max=10.0)

    imgui.text(f"edited: {imgui.is_item_edited()}")
    imgui.text(f"activated: {imgui.is_item_activated()}")
    imgui.text(f"finished: {imgui.is_item_deactivated_after_edit()}")

is_item_activated
^^^^^^^^^^^^^^^^^

.. imgui-signature:: is_item_activated

``True`` on the frame the element became active, e.g. the frame a drag started.

**Parameters**

none

.. imgui-example::
    :interact: press 60 18

    sigma = 1.4

    changed, sigma = imgui.slider_float("sigma", v=sigma, v_min=0.1, v_max=10.0)
    imgui.text(f"activated: {imgui.is_item_activated()}")

is_item_deactivated_after_edit
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. imgui-signature:: is_item_deactivated_after_edit

``True`` only on the frame an edit ends, which is what to use for work that is too expensive to run while a
slider is being dragged.

**Parameters**

none

.. imgui-example::
    :interact: drag 60 18 100 18; release

    sigma = 1.4

    changed, sigma = imgui.slider_float("sigma", v=sigma, v_min=0.1, v_max=10.0)
    imgui.text(f"finished: {imgui.is_item_deactivated_after_edit()}")

is_any_item_hovered
^^^^^^^^^^^^^^^^^^^

.. imgui-signature:: is_any_item_hovered

.. imgui-example::
    :interact: hover 30 18

    imgui.button("autoscale")
    imgui.button("center")

    imgui.text(f"any hovered: {imgui.is_any_item_hovered()}")

is_window_hovered
^^^^^^^^^^^^^^^^^

.. imgui-signature:: is_window_hovered

.. imgui-example::
    :interact: hover 60 40

    imgui.text(f"window hovered: {imgui.is_window_hovered()}")

is_window_focused
^^^^^^^^^^^^^^^^^

.. imgui-signature:: is_window_focused

.. imgui-example::
    :interact: click 60 40

    imgui.text(f"window focused: {imgui.is_window_focused()}")

is_window_appearing
^^^^^^^^^^^^^^^^^^^

.. imgui-signature:: is_window_appearing

``True`` on the first frame the window is drawn, for setup that should happen once, such as sizing a table column.

**Parameters**

none

.. imgui-example::

    imgui.text(f"appearing: {imgui.is_window_appearing()}")

is_mouse_down
^^^^^^^^^^^^^

.. imgui-signature:: is_mouse_down

These ask about the mouse anywhere, not about an element. A right-click that should open something belongs in
``begin_popup_context_item`` instead.

**Parameters**

* ``button`` - ``0`` left, ``1`` right, ``2`` middle
* ``repeat`` - report repeats while the button is held

.. imgui-example::
    :name: is_mouse_down
    :interact: press 60 40

    imgui.text(f"left down: {imgui.is_mouse_down(0)}")
    imgui.text(f"left clicked: {imgui.is_mouse_clicked(0)}")
    imgui.text(f"right down: {imgui.is_mouse_down(1)}")

is_mouse_clicked
^^^^^^^^^^^^^^^^

.. imgui-signature:: is_mouse_clicked

``True`` on the frame the button goes down.

**Parameters**

* ``button`` - ``0`` left, ``1`` right, ``2`` middle
* ``repeat`` - report repeats while the button is held

.. imgui-example::
    :interact: press 60 30

    imgui.text(f"left clicked: {imgui.is_mouse_clicked(0)}")

is_mouse_released
^^^^^^^^^^^^^^^^^

.. imgui-signature:: is_mouse_released

``True`` on the frame the button goes up.

**Parameters**

* ``button`` - ``0`` left, ``1`` right, ``2`` middle

.. imgui-example::
    :interact: click 60 30

    imgui.text(f"left released: {imgui.is_mouse_released(0)}")

is_mouse_double_clicked
^^^^^^^^^^^^^^^^^^^^^^^

.. imgui-signature:: is_mouse_double_clicked

``True`` on the frame of the second click of a double click.

**Parameters**

* ``button`` - ``0`` left, ``1`` right, ``2`` middle

.. imgui-example::
    :interact: double_click 60 30

    imgui.text(f"double clicked: {imgui.is_mouse_double_clicked(0)}")

is_mouse_dragging
^^^^^^^^^^^^^^^^^

.. imgui-signature:: is_mouse_dragging

The delta is measured from where the button went down. Reset it each frame to get the movement since the last frame,
which is what a drag handle needs.

**Parameters**

* ``button`` - ``0`` left, ``1`` right, ``2`` middle
* ``lock_threshold`` - how far the pointer must move before it counts as a drag, the default uses the style threshold

.. imgui-example::
    :name: is_mouse_dragging
    :interact: drag 40 30 90 45

    delta = imgui.get_mouse_drag_delta(0)

    imgui.text(f"dragging: {imgui.is_mouse_dragging(0)}")
    imgui.text(f"delta: {delta.x:.0f}, {delta.y:.0f}")

get_mouse_drag_delta
^^^^^^^^^^^^^^^^^^^^

.. imgui-signature:: get_mouse_drag_delta

The movement since the button went down, in pixels.

**Parameters**

* ``button`` - ``0`` left, ``1`` right, ``2`` middle
* ``lock_threshold`` - how far the pointer must move before it counts as a drag

**Returns:** the delta, use ``.x`` and ``.y``

.. imgui-example::
    :interact: drag 40 30 90 45

    delta = imgui.get_mouse_drag_delta(0)

    imgui.text(f"delta: {delta.x:.0f}, {delta.y:.0f}")

reset_mouse_drag_delta
^^^^^^^^^^^^^^^^^^^^^^

.. imgui-signature:: reset_mouse_drag_delta

Sets the delta back to zero, call it each frame to get the movement since the last frame rather than since the
button went down.

**Parameters**

* ``button`` - ``0`` left, ``1`` right, ``2`` middle

get_mouse_pos
^^^^^^^^^^^^^

.. imgui-signature:: get_mouse_pos

**Parameters**

none

**Returns:** the pointer position in canvas coordinates, use ``.x`` and ``.y``

.. imgui-example::
    :interact: hover 70 30

    position = imgui.get_mouse_pos()

    imgui.text(f"pointer: {position.x:.0f}, {position.y:.0f}")

is_key_pressed
^^^^^^^^^^^^^^

.. imgui-signature:: is_key_pressed

**Parameters**

* ``key`` - an ``imgui.Key`` member, e.g. ``imgui.Key.right_arrow``
* ``repeat`` - report repeats while the key is held

.. imgui-example::
    :name: is_key_pressed
    :interact: hover 60 30; key right_arrow

    index = 42

    if imgui.is_key_pressed(imgui.Key.right_arrow):
        index += 1

    if imgui.is_key_pressed(imgui.Key.left_arrow):
        index -= 1

    imgui.text(f"index: {index}")

is_key_down
^^^^^^^^^^^

.. imgui-signature:: is_key_down

``True`` while the key is held, rather than only on the frame it goes down.

**Parameters**

* ``key`` - an ``imgui.Key`` member

.. imgui-example::
    :interact: hover 60 30; key left_shift

    imgui.text(f"shift held: {imgui.is_key_down(imgui.Key.left_shift)}")

get_io
^^^^^^

.. imgui-signature:: get_io

The imgui io structure. ``want_capture_mouse`` is the field to know about: it is ``True`` while imgui is using the
pointer, and fastplotlib relies on it to keep clicks on a UI from reaching the plot.

**Parameters**

none

**Returns:** an ``imgui.IO``

.. imgui-example::
    :interact: hover 60 30

    io = imgui.get_io()

    imgui.text(f"framerate: {io.framerate:.0f}")
    imgui.text(f"capture mouse: {io.want_capture_mouse}")

Plots
-----

These draw a small line plot or histogram from an array of values, for a preview next to the controls. They are not a
plotting library, a fastplotlib subplot is.

``values`` must be a contiguous ``float32`` array.

plot_lines
^^^^^^^^^^

.. imgui-signature:: plot_lines

**Parameters**

* ``label`` - drawn to the right of the plot, ``"##hidden"`` suppresses it
* ``values`` - the values to plot
* ``values_offset`` - index to start from, for a ring buffer
* ``overlay_text`` - text drawn over the plot
* ``scale_min``, ``scale_max`` - the y range, the default fits the values
* ``graph_size`` - ``(width, height)``, a zero component is a default size
* ``stride`` - byte stride between values, for a column of a 2d array

.. imgui-example::

    values = np.sin(np.linspace(0, 4 * np.pi, 100)).astype(np.float32)

    imgui.plot_lines("##trace", values, graph_size=(220, 60), overlay_text="channel 0")

plot_histogram
^^^^^^^^^^^^^^

.. imgui-signature:: plot_histogram

**Parameters**

* ``label`` - drawn to the right of the plot
* ``values`` - the bin counts
* ``values_offset`` - index to start from
* ``overlay_text`` - text drawn over the plot
* ``scale_min``, ``scale_max`` - the y range, the default fits the values
* ``graph_size`` - ``(width, height)``, a zero component is a default size
* ``stride`` - byte stride between values

.. imgui-example::

    data = np.random.normal(loc=120, scale=30, size=100_000)
    counts = np.histogram(data, bins=64)[0].astype(np.float32)

    imgui.plot_histogram("##histogram", counts, graph_size=(220, 60))

image
^^^^^

.. imgui-signature:: image

Draws a texture that you have uploaded to the GPU and registered with the imgui renderer, which is how
``ImguiColorbar`` draws its colormap bar. There is no example here because the texture has to come from the wgpu
device of the Figure::

    texture_ref = figure.imgui_renderer.backend.register_texture(texture.create_view())
    imgui.image(texture_ref, (24, 200))

**Parameters**

* ``tex_ref`` - an ``imgui.ImTextureRef`` from ``register_texture``
* ``image_size`` - ``(width, height)`` to draw it at
* ``uv0``, ``uv1`` - the region of the texture to draw, ``(0, 0)`` to ``(1, 1)`` by default

image_button
^^^^^^^^^^^^

.. imgui-signature:: image_button

``image`` that responds to a click.

**Parameters**

* ``str_id`` - identifies the button
* ``tex_ref`` - an ``imgui.ImTextureRef`` from ``register_texture``
* ``image_size`` - ``(width, height)`` to draw it at
* ``uv0``, ``uv1`` - the region of the texture to draw
* ``bg_col``, ``tint_col`` - background drawn behind the image, and a color the image is multiplied by

**Returns:** ``True`` on the frame the button is clicked

Tables
------

A table is opened with ``begin_table``, and ``end_table`` is called only when it returned ``True``. Cells are filled by
walking rows and columns, either with ``table_next_column`` or by setting the column index.

begin_table
^^^^^^^^^^^

.. imgui-signature:: begin_table

**Parameters**

* ``str_id`` - identifies the table
* ``columns`` - how many columns
* ``outer_size`` - ``(width, height)`` of the table, a zero height fits the rows
* ``inner_width`` - width of the scrolling region when the table scrolls horizontally

.. imgui-example::
    :name: begin_table

    graphics = [("line-1", "LineGraphic", True), ("image-1", "ImageGraphic", False)]

    if imgui.begin_table("graphics", 3, flags=imgui.TableFlags_.borders):
        for name, kind, visible in graphics:
            imgui.table_next_row()

            imgui.table_next_column()
            imgui.text(name)

            imgui.table_next_column()
            imgui.text(kind)

            imgui.table_next_column()
            imgui.text("visible" if visible else "hidden")

        imgui.end_table()

end_table
^^^^^^^^^

.. imgui-signature:: end_table

Call it only when the matching ``begin_table`` returned ``True``.

**Parameters**

none

table_next_row
^^^^^^^^^^^^^^

.. imgui-signature:: table_next_row

**Parameters**

* ``min_row_height`` - minimum height of the row in pixels

.. imgui-example::

    if imgui.begin_table("frames", 2, flags=imgui.TableFlags_.borders):
        for index in range(3):
            imgui.table_next_row(min_row_height=24)

            imgui.table_next_column()
            imgui.text(f"frame {index}")

            imgui.table_next_column()
            imgui.text(f"{index * 40} ms")

        imgui.end_table()

table_next_column
^^^^^^^^^^^^^^^^^

.. imgui-signature:: table_next_column

``table_next_column`` moves to the next cell, wrapping to the first column of the next row. Use
``table_set_column_index`` to fill cells out of order.

**Parameters**

* ``column_n`` - the column to move to

**Returns:** ``True`` when the column is visible, a clipped or hidden column can be skipped

.. imgui-example::
    :name: table_set_column_index

    if imgui.begin_table("stats", 2, flags=imgui.TableFlags_.borders):
        for label, value in [("vmin", "12"), ("vmax", "208")]:
            imgui.table_next_row()

            imgui.table_set_column_index(0)
            imgui.text(label)

            imgui.table_set_column_index(1)
            imgui.text(value)

        imgui.end_table()

table_set_column_index
^^^^^^^^^^^^^^^^^^^^^^

.. imgui-signature:: table_set_column_index

Fills a cell out of order, rather than moving to the next one.

**Parameters**

* ``column_n`` - the column to move to

**Returns:** ``True`` when the column is visible

table_setup_column
^^^^^^^^^^^^^^^^^^

.. imgui-signature:: table_setup_column

Declare the columns before any row, then ``table_headers_row`` draws one row with their labels.

**Parameters**

* ``label`` - the column header
* ``init_width_or_weight`` - a starting width in pixels, or a share of the table width for a stretched column.
  imgui rejects it unless the sizing policy is explicit, so pass ``imgui.TableColumnFlags_.width_fixed`` or
  ``width_stretch`` with it
* ``user_id`` - an id you can read back when sorting

.. imgui-example::
    :name: table_headers_row

    if imgui.begin_table("graphics", 2, flags=imgui.TableFlags_.borders):
        imgui.table_setup_column("name", flags=imgui.TableColumnFlags_.width_fixed, init_width_or_weight=90)
        imgui.table_setup_column("type")
        imgui.table_headers_row()

        for name, kind in [("line-1", "LineGraphic"), ("image-1", "ImageGraphic")]:
            imgui.table_next_row()

            imgui.table_next_column()
            imgui.text(name)

            imgui.table_next_column()
            imgui.text(kind)

        imgui.end_table()

table_headers_row
^^^^^^^^^^^^^^^^^

.. imgui-signature:: table_headers_row

Draws one row of headers from the labels given to ``table_setup_column``.

**Parameters**

none
