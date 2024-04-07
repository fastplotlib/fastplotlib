from datetime import datetime
from math import copysign
import traceback

from ...utils.gui import QtWidgets
from ...graphics.selectors import PolygonSelector
from ._toolbar import ToolBar
from ._qtoolbar_template import Ui_QToolbar


class QToolbar(
    ToolBar, QtWidgets.QWidget
):  # inheritance order MUST be Toolbar first, QWidget second! Else breaks
    """Toolbar for Qt context"""

    def __init__(self, output_context, figure):
        QtWidgets.QWidget.__init__(self, parent=output_context)
        ToolBar.__init__(self, figure)

        # initialize UI
        self.ui = Ui_QToolbar()
        self.ui.setupUi(self)

        # connect button events
        self.ui.auto_scale_button.clicked.connect(self.auto_scale_handler)
        self.ui.center_button.clicked.connect(self.center_scene_handler)
        self.ui.panzoom_button.toggled.connect(self.panzoom_handler)
        self.ui.maintain_aspect_button.toggled.connect(self.maintain_aspect_handler)
        self.ui.y_direction_button.clicked.connect(self.y_direction_handler)

        # subplot labels update when a user click on subplots
        subplot = self.figure[0, 0]
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
        self.figure.renderer.add_event_handler(self.update_current_subplot, "click")

        self.setMaximumHeight(35)

        # set the initial values for buttons
        self.ui.maintain_aspect_button.setChecked(
            self.current_subplot.camera.maintain_aspect
        )
        self.ui.panzoom_button.setChecked(self.current_subplot.controller.enabled)

        if copysign(1, self.current_subplot.camera.local.scale_y) == -1:
            self.ui.y_direction_button.setText("v")
        else:
            self.ui.y_direction_button.setText("^")

    def update_current_subplot(self, ev):
        """update the text label for the current subplot"""
        for subplot in self.figure:
            pos = subplot.map_screen_to_world((ev.x, ev.y))
            if pos is not None:
                if subplot.name is not None:
                    name = subplot.name
                else:
                    name = str(subplot.position)
                self.ui.current_subplot.setText(name)

                # set buttons w.r.t. current subplot
                self.ui.panzoom_button.setChecked(subplot.controller.enabled)
                self.ui.maintain_aspect_button.setChecked(
                    subplot.camera.maintain_aspect
                )

                if copysign(1, subplot.camera.local.scale_y) == -1:
                    self.ui.y_direction_button.setText("v")
                else:
                    self.ui.y_direction_button.setText("^")

    def _get_subplot_dropdown_value(self) -> str:
        return self.ui.current_subplot.text()

    def auto_scale_handler(self, *args):
        self.current_subplot.auto_scale(
            maintain_aspect=self.current_subplot.camera.maintain_aspect
        )

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
                self.figure.record_start(
                    f"./{datetime.now().isoformat(timespec='seconds').replace(':', '_')}.mp4"
                )
            except Exception:
                traceback.print_exc()
                self.ui.record_button.setChecked(False)
        else:
            self.figure.record_stop()

    def add_polygon(self, *args):
        ps = PolygonSelector(edge_width=3, edge_color="mageneta")
        self.current_subplot.add_graphic(ps, center=False)
