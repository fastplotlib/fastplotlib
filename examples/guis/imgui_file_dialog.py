"""
File Dialog Data Loader
=======================

Example showing how to use portable file dialogs to dynamically load
image data into an ImageWidget.

Supported filetypes: https://imageio.readthedocs.io/en/stable/formats/index.html

Demonstrates:
- Creating a custom EdgeWindow GUI panel
- Using portable_file_dialogs for native file/folder selection
- Dynamically updating ImageWidget data
"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'screenshot'

from pathlib import Path

import numpy as np
import imageio.v3 as iio

import fastplotlib as fpl

# subclass from EdgeWindow to create a custom ImGUI panel
from fastplotlib.ui import EdgeWindow
from imgui_bundle import imgui, portable_file_dialogs as pfd


# generate initial synthetic data: a 4D array (t, z, y, x) simulating a time-lapse volume
np.random.seed(42)
n_timepoints, n_slices, height, width = 10, 5, 128, 128

# create a moving gaussian blob across time and z-slices
data = np.zeros((n_timepoints, n_slices, height, width), dtype=np.float32)
for t in range(n_timepoints):
    for z in range(n_slices):
        # create gaussian blob with position varying by time and z
        y_center = height // 2 + int(20 * np.sin(2 * np.pi * t / n_timepoints))
        x_center = width // 2 + int(20 * np.cos(2 * np.pi * t / n_timepoints))
        y, x = np.ogrid[:height, :width]
        blob = np.exp(
            -((y - y_center) ** 2 + (x - x_center) ** 2) / (2 * (10 + z * 2) ** 2)
        )
        data[t, z] = blob + np.random.normal(0, 0.05, (height, width))

# create ImageWidget with the synthetic data
iw = fpl.ImageWidget(
    data=[data],
    names=["Synthetic Volume"],
    slider_dim_names=("t", "z"),
    figure_kwargs={"size": (900, 600)},
)


class DataLoaderWidget(EdgeWindow):
    """
    Customizable widget with file selection via portable file dialog.

    Parameters
    ----------
    image_widget : fpl.ImageWidget
        The ImageWidget instance to update with loaded data.
    initial_path : str
        Initial path to display in the path input field.
    """

    def __init__(self, image_widget, initial_path: str = ""):
        super().__init__(
            figure=image_widget.figure,
            size=280,
            location="right",
            title="Data Loader",
        )
        self._iw = image_widget
        self._current_path = initial_path
        self._status_msg = ""
        self._status_color = imgui.ImVec4(1.0, 1.0, 1.0, 1.0)

        # dialog state - None when no dialog is open
        self._folder_dialog = None
        self._file_dialog = None

        self._current_data_shape = data.shape


def update(self):
    """Render the ImGui interface. Called each frame by the figure."""

    # Imgui colors are in normalized RGBA (Red, Green, Blue, Alpha) with values in the range [0.0, 1.0].
    # e.g. imgui.ImVec4(0.4, 0.8, 1.0, 1.0)
    #
    # To preview these colors in a web tool, you'll need to convert them to 8-bit RGB (0-255).
    # Multiply each component by 255:
    # RGB: (0.4 * 255 = 102, 0.8 * 255 = 204, 1 * 255 = 255)
    # Sky blue

    imgui.push_style_var(imgui.StyleVar_.item_spacing, imgui.ImVec2(8, 6))
    imgui.push_style_var(imgui.StyleVar_.frame_padding, imgui.ImVec2(6, 4))

    imgui.spacing()

    # sky blue header
    imgui.text_colored(imgui.ImVec4(0.4, 0.8, 1.0, 1.0), "Load New Dataset")
    imgui.separator()
    imgui.spacing()

    imgui.text("Current Data Shape:")
    imgui.indent()
    # light gray text
    imgui.text_colored(
        imgui.ImVec4(0.7, 0.7, 0.7, 1.0), f"Shape: {self._current_data_shape}"
    )
    imgui.unindent()
    imgui.spacing()

    # path input section
    imgui.text("Data Path:")
    avail_width = imgui.get_content_region_avail().x
    imgui.set_next_item_width(avail_width)
    changed, new_path = imgui.input_text("##path", self._current_path)
    if changed:
        self._current_path = new_path

    imgui.spacing()

    # file/folder dialog buttons
    button_width = (avail_width - 8) / 2

    # blue button theme
    imgui.push_style_color(
        imgui.Col_.button, imgui.ImVec4(0.2, 0.3, 0.5, 1.0)
    )  # dark blue
    imgui.push_style_color(
        imgui.Col_.button_hovered,
        imgui.ImVec4(0.3, 0.4, 0.6, 1.0),  # lighter blue on hover
    )
    imgui.push_style_color(
        imgui.Col_.button_active,
        imgui.ImVec4(0.1, 0.2, 0.4, 1.0),  # darker blue when clicked
    )

    if imgui.button("Open File", imgui.ImVec2(button_width, 0)):
        # determine starting directory for the dialog
        start_dir = (
            str(Path(self._current_path).parent)
            if Path(self._current_path).exists()
            else str(Path.home())
        )
        # open native file dialog with common image format filters
        self._file_dialog = pfd.open_file(
            "Select Image File",
            start_dir,
            [
                "Image Files",
                "*.tif *.tiff *.png *.jpg *.jpeg",
                "TIFF Files",
                "*.tif *.tiff",
                "All Files",
                "*.*",
            ],
        )

    imgui.same_line()

    if imgui.button("Open Folder", imgui.ImVec2(button_width, 0)):
        start_dir = (
            self._current_path
            if Path(self._current_path).exists()
            else str(Path.home())
        )
        # open native folder selection dialog
        self._folder_dialog = pfd.select_folder("Select Data Folder", start_dir)

    imgui.pop_style_color(3)

    imgui.spacing()

    # green load button theme
    imgui.push_style_color(
        imgui.Col_.button, imgui.ImVec4(0.2, 0.5, 0.2, 1.0)
    )  # dark green
    imgui.push_style_color(
        imgui.Col_.button_hovered,
        imgui.ImVec4(0.3, 0.7, 0.3, 1.0),  # lighter green on hover
    )
    imgui.push_style_color(
        imgui.Col_.button_active,
        imgui.ImVec4(0.1, 0.4, 0.1, 1.0),  # darker green when clicked
    )
    if imgui.button("Load Data", imgui.ImVec2(avail_width, 0)):
        self._load_data()
    imgui.pop_style_color(3)

    # check for dialog results (non-blocking)
    if self._file_dialog is not None and self._file_dialog.ready():
        result = self._file_dialog.result()
        if result and len(result) > 0:
            self._current_path = result[0]
        self._file_dialog = None

    if self._folder_dialog is not None and self._folder_dialog.ready():
        result = self._folder_dialog.result()
        if result:
            self._current_path = result
        self._folder_dialog = None

    # status message section
    imgui.spacing()
    imgui.separator()
    imgui.spacing()

    if self._status_msg:
        # wrap long status messages
        imgui.push_text_wrap_pos(imgui.get_content_region_avail().x)
        imgui.text_colored(self._status_color, self._status_msg)
        imgui.pop_text_wrap_pos()

    imgui.pop_style_var(2)


def _load_data(self):
    """
    Load image data from the current path and update the ImageWidget.

    Supports any format that imageio can read (TIFF, PNG, JPEG, etc.).
    Updates status message to reflect success or failure.
    """
    if not self._current_path:
        self._status_msg = "Error: No path specified"
        self._status_color = imgui.ImVec4(1.0, 0.3, 0.3, 1.0)  # red for errors
        return

    path = Path(self._current_path)
    if not path.exists():
        self._status_msg = "Error: Path does not exist"
        self._status_color = imgui.ImVec4(1.0, 0.3, 0.3, 1.0)  # red for errors
        return

    try:
        self._status_msg = "Loading..."
        self._status_color = imgui.ImVec4(
            1.0, 0.8, 0.2, 1.0
        )  # yellow/orange for loading

        # use imageio to read the image file
        new_data = iio.imread(self._current_path)

        # update ImageWidget data using array API
        self._iw.data[0] = new_data

        # reset slider indices
        self._iw.indices["t"] = 0
        if new_data.ndim >= 4 and "z" in self._iw.indices:
            self._iw.indices["z"] = 0

        self._current_data_shape = new_data.shape
        self._status_msg = f"Loaded!\nShape: {new_data.shape}"
        self._status_color = imgui.ImVec4(0.3, 1.0, 0.3, 1.0)  # green for success
        print(f"Loaded: {self._current_path}, shape: {new_data.shape}")

    except Exception as e:
        self._status_msg = f"Error: {str(e)}"
        self._status_color = imgui.ImVec4(1.0, 0.3, 0.3, 1.0)  # red for errors
        print(f"Error loading data: {e}")


# show the ImageWidget
iw.show()

# create and add the data loader widget to the figure
loader = DataLoaderWidget(iw, initial_path="")
iw.figure.add_gui(loader)

# required for sphinx gallery
figure = iw.figure


# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
