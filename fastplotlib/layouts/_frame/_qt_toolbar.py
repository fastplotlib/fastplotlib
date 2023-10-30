from datetime import datetime
from functools import partial
from itertools import product
from math import copysign
import traceback
from typing import *

from PyQt6 import QtWidgets, QtCore

from ...graphics.selectors import PolygonSelector
from ._toolbar import ToolBar
from ._qtoolbar_template import Ui_QToolbar


class QToolbar(ToolBar, QtWidgets.QWidget):
    def __init__(self, output_context, plot):
        QtWidgets.QWidget.__init__(self, parent=output_context)
        ToolBar.__init__(self, plot)

        self.ui = Ui_QToolbar()
        self.ui.setupUi(self)

        self.ui.auto_scale_button.clicked.connect(self.auto_scale_handler)
        self.ui.center_button.clicked.connect(self.center_scene_handler)
        self.ui.panzoom_button.toggled.connect(self.panzoom_handler)
        self.ui.maintain_aspect_button.toggled.connect(self.maintain_aspect_handler)
        self.ui.y_direction_button.clicked.connect(self.y_direction_handler)

        if hasattr(self.plot, "_subplots"):
            subplot = self.plot[0, 0]
            # set label from first subplot name
            if subplot.name is not None:
                name = subplot.name
            else:
                name = str(subplot.position)

            self.ui.current_subplot = QtWidgets.QLabel(parent=self)
            self.ui.current_subplot.setText(name)
            self.ui.horizontalLayout.addWidget(self.ui.current_subplot)

            self.plot.renderer.add_event_handler(self.update_current_subplot, "click")

        self.setMaximumHeight(40)

        # set the initial values
        self.ui.maintain_aspect_button.setChecked(self.current_subplot.camera.maintain_aspect)
        self.ui.panzoom_button.setChecked(self.current_subplot.controller.enabled)

        if copysign(1, self.current_subplot.camera.local.scale_y) == -1:
            self.ui.y_direction_button.setText("v")
        else:
            self.ui.y_direction_button.setText("^")

    def update_current_subplot(self, ev):
        for subplot in self.plot:
            pos = subplot.map_screen_to_world((ev.x, ev.y))
            if pos is not None:
                # update self.dropdown
                if subplot.name is None:
                    self._dropdown.value = str(subplot.position)
                else:
                    self._dropdown.value = subplot.name
                self._panzoom_controller_button.value = subplot.controller.enabled
                self._maintain_aspect_button.value = subplot.camera.maintain_aspect

    def _get_subplot_dropdown_value(self) -> str:
        return self.ui.current_subplot.text()

    def auto_scale_handler(self, *args):
        self.current_subplot.auto_scale(maintain_aspect=self.current_subplot.camera.maintain_aspect)

    def center_scene_handler(self, *args):
        self.current_subplot.center_scene()

    def panzoom_handler(self, value: bool):
        self.current_subplot.controller.enabled = value

    def maintain_aspect_handler(self, value: bool):
        for camera in self.current_subplot.controller.cameras:
            camera.maintain_aspect = value

    def y_direction_handler(self, *args):
        # TODO: What if the user has set different y_scales for cameras under the same controller?
        self.current_subplot.camera.local.scale_y *= -1
        if self.current_subplot.camera.local.scale_y == -1:
            self.ui.y_direction_button.setText("v")
        else:
            self.ui.y_direction_button.setText("^")

    def record_handler(self, ev):
        if self.ui.record_button.isChecked():
            try:
                self.plot.record_start(
                    f"./{datetime.now().isoformat(timespec='seconds').replace(':', '_')}.mp4"
                )
            except Exception:
                traceback.print_exc()
                self.ui.record_button.setChecked(False)
        else:
            self.plot.record_stop()

    def add_polygon(self, *args):
        ps = PolygonSelector(edge_width=3, edge_color="mageneta")
        self.current_subplot.add_graphic(ps, center=False)


# TODO: There must be a better way to do this
# TODO: Check if an interface exists between ipywidgets and Qt
class SliderInterface:
    def __init__(self, qslider):
        self.qslider = qslider

    @property
    def value(self) -> int:
        return self.qslider.value()

    @value.setter
    def value(self, value: int):
        self.qslider.setValue(value)

    @property
    def max(self) -> int:
        return self.qslider.maximum()

    @max.setter
    def max(self, value: int):
        self.qslider.setMaximum(value)

    @property
    def min(self):
        return self.qslider.minimum()

    @min.setter
    def min(self, value: int):
        self.qslider.setMinimum(value)


class QToolbarImageWidget(QtWidgets.QWidget):
    """Toolbar for ImageWidget"""
    def __init__(self, image_widget):
        QtWidgets.QWidget.__init__(self)

        self.vlayout = QtWidgets.QVBoxLayout(self)

        self.image_widget = image_widget

        self.reset_vmin_vmax_button = QtWidgets.QPushButton(self)
        self.reset_vmin_vmax_button.setText("auto-contrast")
        self.reset_vmin_vmax_button.clicked.connect(self.image_widget.reset_vmin_vmax)
        self.vlayout.addWidget(self.reset_vmin_vmax_button)

        self.sliders: Dict[str, SliderInterface] = dict()

        # has time and/or z-volume
        if self.image_widget.ndim > 2:
            for dim in self.image_widget.slider_dims:
                hlayout = QtWidgets.QHBoxLayout()
                max_val = self.image_widget._dims_max_bounds[dim] - 1

                slider = QtWidgets.QSlider(self)
                slider.setOrientation(QtCore.Qt.Orientation.Horizontal)
                slider.setMinimum(0)
                slider.setMaximum(max_val)
                slider.setValue(0)
                slider.setSingleStep(1)
                slider.setPageStep(10)

                spinbox = QtWidgets.QSpinBox(self)
                spinbox.setMinimum(0)
                spinbox.setMaximum(max_val)
                spinbox.setValue(0)
                spinbox.setSingleStep(1)

                slider.valueChanged.connect(spinbox.setValue)
                spinbox.valueChanged.connect(slider.setValue)

                slider.valueChanged.connect(partial(self.image_widget._slider_value_changed, dim))

                slider_label = QtWidgets.QLabel(self)
                slider_label.setText(dim)

                hlayout.addWidget(slider_label)
                hlayout.addWidget(slider)
                hlayout.addWidget(spinbox)

                self.vlayout.addLayout(hlayout)
                self.sliders[dim] = SliderInterface(slider)

        max_height = 40 + (40 * len(self.sliders.keys()))

        self.setMaximumHeight(max_height)
