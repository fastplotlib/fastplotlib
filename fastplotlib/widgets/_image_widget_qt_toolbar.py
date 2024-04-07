from functools import partial
from typing import Dict

from fastplotlib.utils.gui import QtWidgets, QtCore

# TODO: There must be a better way to do this
# TODO: Check if an interface exists between ipywidgets and Qt
# TODO: Or we won't need it anyways once we have UI in pygfx
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
        self.reset_vmin_vmax_hlut_button.clicked.connect(
            self.image_widget.reset_vmin_vmax_frame
        )
        hlayout_buttons.addWidget(self.reset_vmin_vmax_hlut_button)

        self.vlayout.addLayout(hlayout_buttons)

        self.sliders: Dict[str, SliderInterface] = dict()

        # has time and/or z-volume
        if self.image_widget.ndim > 2:
            # create a slider, spinbox and dimension label for each dimension in the ImageWidget
            for dim in self.image_widget.slider_dims:
                hlayout = (
                    QtWidgets.QHBoxLayout()
                )  # horizontal stack for label, slider, spinbox

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
                slider.valueChanged.connect(
                    partial(self.image_widget._slider_value_changed, dim)
                )

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
