"""
ImGUI menu bar
==============

You can override ``ImguiWindow.draw()`` to create a window with a menu bar. You can override the `draw()` call when
you need full control of the imgui window.
"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'screenshot'

import imageio.v3 as iio
import fastplotlib as fpl
from fastplotlib.ui import ImguiWindow
from imgui_bundle import imgui

# the imageio standard images
IMAGES = [
    "camera.png",
    "astronaut.png",
    "checkerboard.png",
    "chelsea.png",
    "clock.png",
    "coffee.png",
    "coins.png",
    "horse.png",
    "hubble_deep_field.png",
    "immunohistochemistry.png",
    "moon.png",
    "page.png",
    "text.png",
    "wikkie.png",
    "bricks.jpg",
    "wood.jpg",
]

figure = fpl.Figure(size=(700, 560))
image = figure[0, 0].add_image(iio.imread(f"imageio:{IMAGES[0]}"), name="image")


class ImagePicker(ImguiWindow):
    """floating window that replaces the image in the subplot with the one that is picked"""

    def __init__(self):
        super().__init__()

        self.visible = False
        self.picked = IMAGES[0]

    def draw(self):
        if not self.visible:
            return

        # a height of zero makes imgui auto-size the window to fit the list
        imgui.set_next_window_size((220, 0), imgui.Cond_.appearing)
        expanded, self.visible = imgui.begin("Open image", True)

        if expanded:
            for name in IMAGES:
                if imgui.selectable(name, name == self.picked)[0]:
                    self.picked = name
                    image.data = iio.imread(f"imageio:{name}")
                    figure[0, 0].auto_scale()
                    self.visible = False

        imgui.end()


class MenuBar(ImguiWindow):
    """menu bar at the top of the Figure, ``update()`` is unused since ``draw()`` is fully overridden"""

    def __init__(self, picker: ImagePicker):
        super().__init__()

        self._picker = picker
        self._show_version = False

    def draw(self):
        imgui.set_next_window_size((self.width, self.height))
        imgui.set_next_window_pos((self.x, self.y))

        imgui.begin(
            f"menu-bar##{self._id_counter}",
            p_open=None,
            flags=imgui.WindowFlags_.no_collapse
            | imgui.WindowFlags_.no_resize
            | imgui.WindowFlags_.no_title_bar
            | imgui.WindowFlags_.no_scrollbar
            | imgui.WindowFlags_.no_bring_to_front_on_focus
            | imgui.WindowFlags_.menu_bar,
        )

        if imgui.begin_menu_bar():
            if imgui.begin_menu("File"):
                if imgui.menu_item("Open", "", False)[0]:
                    self._picker.visible = True

                imgui.end_menu()

            if imgui.begin_menu("Help"):
                if imgui.menu_item("Version", "", False)[0]:
                    self._show_version = True

                imgui.end_menu()

            imgui.end_menu_bar()

        # the popup is opened here and not within the menu, imgui requires that open_popup() and
        # begin_popup_modal() are called for the same window
        if self._show_version:
            self._show_version = False
            imgui.open_popup("Version")

        # center the modal on the canvas
        imgui.set_next_window_pos(
            imgui.get_main_viewport().get_center(), imgui.Cond_.appearing, (0.5, 0.5)
        )

        # p_open draws a close button in the title bar, imgui closes the modal when it is clicked
        if imgui.begin_popup_modal("Version", True, imgui.WindowFlags_.always_auto_resize)[0]:
            imgui.text(f"fastplotlib version: {fpl.__version__}")
            imgui.end_popup()

        imgui.end()


picker = ImagePicker()
figure.add_imgui_window(picker, location="floating")
figure.add_imgui_window(MenuBar(picker), location="top", size=30)

figure.show()


# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
