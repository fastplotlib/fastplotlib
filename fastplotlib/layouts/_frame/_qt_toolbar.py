from datetime import datetime
from itertools import product
from math import copysign
import traceback

from PyQt6 import QtWidgets

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
            positions = list(product(range(self.plot.shape[0]), range(self.plot.shape[1])))
            values = list()
            for pos in positions:
                if self.plot[pos].name is not None:
                    values.append(self.plot[pos].name)
                else:
                    values.append(str(pos))

            self.ui.dropdown = QtWidgets.QComboBox(parent=self)
            self.ui.dropdown.addItems(values)
            self.ui.horizontalLayout.addWidget(self.ui.dropdown)

        self.setMaximumHeight(40)

        # set the initial values
        self.ui.maintain_aspect_button.setChecked(self.current_subplot.camera.maintain_aspect)
        self.ui.panzoom_button.setChecked(self.current_subplot.controller.enabled)

        if copysign(1, self.current_subplot.camera.local.scale_y) == -1:
            self.ui.y_direction_button.setText("v")
        else:
            self.ui.y_direction_button.setText("^")

    def _get_subplot_dropdown_value(self) -> str:
        return self.ui.dropdown.currentText()

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
