from datetime import datetime
from functools import partial
from math import copysign
import traceback
from typing import *

from PyQt6 import QtWidgets, QtCore

from ...graphics.selectors import PolygonSelector
from ._toolbar import ToolBar
from ._qtoolbar_template import Ui_QToolbar


class QToolbar(ToolBar, QtWidgets.QWidget):  # inheritance order MUST be Toolbar first, QWidget second! Else breaks
    """Toolbar for Qt context"""
    def __init__(self, output_context, plot):
        QtWidgets.QWidget.__init__(self, parent=output_context)
        ToolBar.__init__(self, plot)

        # initialize UI
        self.ui = Ui_QToolbar()
        self.ui.setupUi(self)

        # connect button events
        self.ui.auto_scale_button.clicked.connect(self.auto_scale_handler)
        self.ui.center_button.clicked.connect(self.center_scene_handler)
        self.ui.panzoom_button.toggled.connect(self.panzoom_handler)
        self.ui.maintain_aspect_button.toggled.connect(self.maintain_aspect_handler)
        self.ui.y_direction_button.clicked.connect(self.y_direction_handler)

        # the subplot labels that update when a user click on subplots
        if hasattr(self.plot, "_subplots"):
            subplot = self.plot[0, 0]
            # set label from first subplot name
            if subplot.name is not None:
                name = subplot.name
            else:
                name = str(subplot.position)

            # here we will just use a simple label, not a dropdown like ipywidgets
            # the dropdown implementation is tedious with Qt
            self.ui.current_subplot = QtWidgets.QLabel(parent=self)
            self.ui.current_subplot.setText(name)
            self.ui.horizontalLayout.addWidget(self.ui.current_subplot)

            # update the subplot label when a subplot is clicked into
            self.plot.renderer.add_event_handler(self.update_current_subplot, "click")

        self.setMaximumHeight(35)

        # set the initial values for buttons
        self.ui.maintain_aspect_button.setChecked(self.current_subplot.camera.maintain_aspect)
        self.ui.panzoom_button.setChecked(self.current_subplot.controller.enabled)

        if copysign(1, self.current_subplot.camera.local.scale_y) == -1:
            self.ui.y_direction_button.setText("v")
        else:
            self.ui.y_direction_button.setText("^")

    def update_current_subplot(self, ev):
        """update the text label for the current subplot"""
        for subplot in self.plot:
            pos = subplot.map_screen_to_world((ev.x, ev.y))
            if pos is not None:
                if subplot.name is not None:
                    name = subplot.name
                else:
                    name = str(subplot.position)
                self.ui.current_subplot.setText(name)

                # set buttons w.r.t. current subplot
                self.ui.panzoom_button.setChecked(subplot.controller.enabled)
                self.ui.maintain_aspect_button.setChecked(subplot.camera.maintain_aspect)

                if copysign(1, subplot.camera.local.scale_y) == -1:
                    self.ui.y_direction_button.setText("v")
                else:
                    self.ui.y_direction_button.setText("^")

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
        # flip every camera under the same controller
        for camera in self.current_subplot.controller.cameras:
            camera.local.scale_y *= -1

        if copysign(1, self.current_subplot.camera.local.scale_y) == -1:
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
    """
    This exists so that ImageWidget has a common interface for Sliders.

    This interface makes a QSlider behave somewhat like a ipywidget IntSlider, enough for ImageWidget to function.
    """
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

        # vertical layout
        self.vlayout = QtWidgets.QVBoxLayout(self)

        self.image_widget = image_widget

        hlayout_buttons = QtWidgets.QHBoxLayout()

        self.reset_vmin_vmax_button = QtWidgets.QPushButton(self)
        self.reset_vmin_vmax_button.setText("auto-contrast")
        self.reset_vmin_vmax_button.clicked.connect(self.image_widget.reset_vmin_vmax)
        hlayout_buttons.addWidget(self.reset_vmin_vmax_button)

        self.reset_vmin_vmax_hlut_button = QtWidgets.QPushButton(self)
        self.reset_vmin_vmax_hlut_button.setText("reset histogram-lut")
        self.reset_vmin_vmax_hlut_button.clicked.connect(self.image_widget.reset_vmin_vmax_frame)
        hlayout_buttons.addWidget(self.reset_vmin_vmax_hlut_button)

        self.vlayout.addLayout(hlayout_buttons)

        self.sliders: Dict[str, SliderInterface] = dict()

        # has time and/or z-volume
        if self.image_widget.ndim > 2:
            # create a slider, spinbox and dimension label for each dimension in the ImageWidget
            for dim in self.image_widget.slider_dims:
                hlayout = QtWidgets.QHBoxLayout()  # horizontal stack for label, slider, spinbox

                # max value for current dimension
                max_val = self.image_widget._dims_max_bounds[dim] - 1

                # make slider
                slider = QtWidgets.QSlider(self)
                slider.setOrientation(QtCore.Qt.Orientation.Horizontal)
                slider.setMinimum(0)
                slider.setMaximum(max_val)
                slider.setValue(0)
                slider.setSingleStep(1)
                slider.setPageStep(10)

                # make spinbox
                spinbox = QtWidgets.QSpinBox(self)
                spinbox.setMinimum(0)
                spinbox.setMaximum(max_val)
                spinbox.setValue(0)
                spinbox.setSingleStep(1)

                # link slider and spinbox
                slider.valueChanged.connect(spinbox.setValue)
                spinbox.valueChanged.connect(slider.setValue)

                # connect slider to change the index within the dimension
                slider.valueChanged.connect(partial(self.image_widget._slider_value_changed, dim))

                # slider dimension label
                slider_label = QtWidgets.QLabel(self)
                slider_label.setText(dim)

                # add the widgets to the horizontal layout
                hlayout.addWidget(slider_label)
                hlayout.addWidget(slider)
                hlayout.addWidget(spinbox)

                # add horizontal layout to the vertical layout
                self.vlayout.addLayout(hlayout)

                # add to sliders dict for easier access to users
                self.sliders[dim] = SliderInterface(slider)

        max_height = 35 + (35 * len(self.sliders.keys()))

        self.setMaximumHeight(max_height)
