imgui UIs
=========

`imgui <https://github.com/pthom/imgui_bundle>`_ UIs are rendered directly onto the same canvas as the ``Figure``, so
the same UI code runs on every GUI backend: glfw, Qt, wx, and jupyter.

imgui support requires ``imgui-bundle``, see the installation section of the user guide. When ``imgui-bundle`` is
installed ``fastplotlib.Figure`` is an ``ImguiFigure``, and every subplot gets a toolbar and a standard right-click
menu.

There are two things you can add to a ``Figure``:

* ``ImguiWindow`` - a window drawn within the Figure. It can float over the plots, be fixed to a rect, or occupy space
  on an edge of the Figure or of a Subplot.
* ``ImguiPopup`` - a popup opened by a right-click on the Figure, a Subplot, or a Graphic.

Both are written in the same way, either as a function or as a subclass.

Floating and fixed windows
--------------------------

A floating window is drawn over the plots. imgui sizes it to fit its contents, it appears at the top left of the
canvas, and the user can move, resize, and collapse it. The function draws the imgui elements and is called on every
render, the object it is added to is an optional argument::

    import numpy as np
    import fastplotlib as fpl
    from imgui_bundle import imgui

    figure = fpl.Figure(size=(700, 560))
    figure[0, 0].add_line(np.random.rand(100), name="line")

    @figure.add_imgui_window(location="floating")
    def gui(fig):
        line = fig[0, 0]["line"]

        changed, thickness = imgui.slider_float("thickness", v=line.thickness, v_min=2.0, v_max=50.0)
        if changed:
            line.thickness = thickness

        if imgui.button("randomize"):
            line.data[:, 1] = np.random.rand(100)

``add_imgui_window`` can also be given the function directly instead of decorating it, which is useful when the same
function is used more than once::

    figure.add_imgui_window(gui, location="floating")

A window can instead be fixed to a ``rect`` of the canvas, ``(x, y, width, height)``, or to an ``extent``,
``(xmin, xmax, ymin, ymax)``. These are fractional if the width and height are ``<= 1``, and in pixels otherwise. A
fixed window cannot be moved, resized, or collapsed::

    @figure.add_imgui_window(extent=(0.6, 0.98, 0.05, 0.25))
    def gui():
        imgui.text("fixed to a fractional extent")

Figure edge windows
-------------------

An edge window occupies canvas space along one edge of the Figure, so it never covers the plots. ``location`` is one of
``"left"``, ``"right"``, ``"top"``, ``"bottom"``, and ``size`` is the thickness in pixels, which is required::

    @figure.add_imgui_window(location="right", size=200, title="controls")
    def gui(fig):
        ...

If ``title`` is not given no title bar is drawn. The "bottom" and "right" Figure edge windows can be resized by
dragging their inner border, and collapsed by double-clicking it.

Subplot edge windows
--------------------

You can add imgui windows that are confined to a subplot edge::

    @figure[0, 0].add_imgui_window(location="right", size=130, title="image")
    def gui(subplot):
        if imgui.button("noise"):
            subplot["image"].data = np.random.rand(128, 128)

Each subplot also has a toolbar, an imgui window at the ``"toolbar"`` location that you can append elements to::

    from imgui_bundle import icons_fontawesome_6 as fa

    @figure[0, 0].append_imgui_window(location="toolbar")
    def toolbar_extra(subplot):
        imgui.same_line()
        _, subplot.axes.visible = imgui.checkbox(fa.ICON_FA_RULER_COMBINED, subplot.axes.visible)

``subplot.toolbar = False`` hides it, and ``add_imgui_window(location="toolbar")`` replaces it.

Appending, replacing, and removing
----------------------------------

Windows are keyed by location, and ``add_imgui_window`` replaces the window at that location.
``append_imgui_window`` adds more UI elements to the window that is already there, it raises if there is none::

    @figure.append_imgui_window(location="right")
    def more(fig):
        imgui.text("appended below the elements of the existing window")

``remove_imgui_window`` removes and returns the window at a location, which can be added again later::

    window = figure.remove_imgui_window("right")

``figure.imgui_windows`` and ``subplot.imgui_windows`` return the windows keyed by location.

Subclassing ``ImguiWindow``
---------------------------

Subclass ``ImguiWindow`` and implement ``update()`` when you need something more complex, such as a UI that keeps
state. Pass what the UI needs into ``__init__``, an instance is not bound to a Figure until it is added::

    from fastplotlib.ui import ImguiWindow

    class Controls(ImguiWindow):
        def __init__(self, line):
            super().__init__()

            self._line = line
            self._ys = line.data[:, 1].copy()
            self._amplitude = 1.0

        def update(self):
            changed, self._amplitude = imgui.slider_float(
                "amplitude", v=self._amplitude, v_min=0.1, v_max=10.0
            )
            if changed:
                self._line.data[:, 1] = self._ys * self._amplitude

    figure.add_imgui_window(Controls(line), location="right", size=200, title="controls")

Within ``update()`` the window's pixel rect is available as ``x``, ``y``, ``width``, and ``height``. ``size`` is
settable, and setting it on an edge or toolbar window triggers a re-layout of the Figure.

``fastplotlib.ui.ChangeFlag`` is useful when several elements modify the same thing. It is a bool that stays ``True``
once it has been set to ``True``::

    from fastplotlib.ui import ChangeFlag

    changed = ChangeFlag(False)
    changed.value, vmin = imgui.slider_float("vmin", v=image.vmin, v_min=0, v_max=255)
    changed.value, vmax = imgui.slider_float("vmax", v=image.vmax, v_min=0, v_max=255)

    if changed:
        image.vmin, image.vmax = vmin, vmax

For full control of the imgui window, override ``draw()`` instead of ``update()``. You are then responsible for
creating the window with ``imgui.begin()`` and ``imgui.end()``, and ``update()`` is not used. This is how you use
window flags that must be set when the window is created, such as ``imgui.WindowFlags_.menu_bar`` for a menu bar. See
the examples gallery.

Right-click popups
------------------

A popup is opened by a right-click. It is not restricted to menu items, any imgui elements can be used.

A popup can be set on the Figure, where it replaces the standard right-click menu, on a Subplot, or on a Graphic. The
most specific one wins: the popup of the graphic under the pointer, else the popup of the subplot that was clicked,
else the popup of the Figure::

    @figure.set_imgui_right_click()
    def popup(fig):
        if imgui.menu_item("autoscale all", "", False)[0]:
            for subplot in fig:
                subplot.auto_scale()

    @figure[0, 1].set_imgui_right_click()
    def subplot_popup(subplot):
        imgui.text(f"subplot: {subplot.name}")

A popup takes the object it is set on as an optional argument, and the function can be passed directly instead of
decorating. Each call wraps the function in its own popup, so the same function can be set on any number of graphics::

    def contrast(image):
        changed, vals = imgui.slider_float2("vmin / vmax", (image.vmin, image.vmax), 0, 255)
        if changed:
            image.vmin, image.vmax = vals

    img1.set_imgui_right_click(contrast)
    img2.set_imgui_right_click(contrast)

Only one popup can be set on an object. A graphic must be added to a subplot of an ``ImguiFigure`` before a popup can
be set on it. ``append_imgui_right_click`` adds more UI elements to the popup that is set,
``remove_imgui_right_click`` removes and returns it, and ``imgui_right_click`` returns the popup that is set.

Extending the standard right-click menu
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The Figure's popup is a ``StandardRightClickMenu``. Append to it to keep its items and add your own::

    @figure.append_imgui_right_click()
    def extra_items(fig):
        imgui.separator()
        _, fig.imgui_show_fps = imgui.checkbox("show fps", fig.imgui_show_fps)

Subclassing ``ImguiPopup``
^^^^^^^^^^^^^^^^^^^^^^^^^^

Subclass ``ImguiPopup`` and implement ``update()``, which contains only the imgui elements. ``subplot`` and ``graphic``
are what the popup was opened on, ``graphic`` is ``None`` if the click was not on a graphic, and ``parent`` is the
object the popup is set on::

    from fastplotlib.ui import ImguiPopup

    class MyPopup(ImguiPopup):
        def update(self):
            imgui.text(f"subplot: {self.subplot.name}")

            if imgui.menu_item("autoscale", "", False)[0]:
                self.subplot.auto_scale()

    figure.set_imgui_right_click(MyPopup())

To keep the standard items, subclass ``StandardRightClickMenu`` and call ``super().update()``::

    from fastplotlib.ui import StandardRightClickMenu

    class MyMenu(StandardRightClickMenu):
        def update(self):
            super().update()

            imgui.separator()
            if imgui.menu_item("my item", "", False)[0]:
                ...

``window_flags`` can be passed to ``set_imgui_right_click`` and is a settable property, and ``is_open`` tells you
whether the popup is currently open.

A window that must stay open after the popup closes cannot be drawn in ``update()``, which only runs while the popup is
open. Override ``draw()`` and draw it after the popup::

    class MyPopup(ImguiPopup):
        def __init__(self):
            super().__init__()
            self._window_open = False

        def update(self):
            if imgui.menu_item("Open window", "", False)[0]:
                self._window_open = True

        def draw(self):
            super().draw()

            if self._window_open:
                _, self._window_open = imgui.begin("my window", True)
                imgui.text("stays open after the popup closes")
                imgui.end()

Built-in imgui UIs
------------------

* ``SubplotToolbar`` - the toolbar of each subplot.
* ``StandardRightClickMenu`` - the Figure's default right-click popup: fps, autoscale, center, maintain aspect, flip
  axes, grids, FOV, and controller options.
* ``ImguiColorbar`` - an ``ImguiWindow`` that shows a colorbar for one or more images, with draggable vmin and vmax, a
  colormap picker, gamma, and an optional precomputed histogram::

      from fastplotlib.ui import ImguiColorbar

      colorbar = ImguiColorbar(images=image, histogram=np.histogram(data, bins=100))
      figure[0, 0].add_imgui_window(colorbar, location="right", size=100)

Writing imgui elements
----------------------

fastplotlib does not wrap imgui, you call ``imgui_bundle`` directly, so any imgui element can be used. See the "GUIs"
section of the examples gallery for complete examples.
