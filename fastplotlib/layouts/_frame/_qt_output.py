from PyQt6 import QtWidgets

from ._qt_toolbar import QToolbar


class QOutputContext(QtWidgets.QWidget):
    def __init__(
            self,
            frame,
            make_toolbar,
            add_widgets,
    ):
        QtWidgets.QWidget.__init__(self, parent=None)
        self.frame = frame
        self.toolbar = None

        self.vlayout = QtWidgets.QVBoxLayout(self)
        self.vlayout.addWidget(self.frame.canvas)

        if make_toolbar:
            self.toolbar = QToolbar(output_context=self, plot=frame)
            self.vlayout.addWidget(self.toolbar)

        if add_widgets is not None:
            for w in add_widgets:
                w.setParent(self)
                self.vlayout.addWidget(w)

        self.setLayout(self.vlayout)

        self.resize(*self.frame._starting_size)

        self.show()

    def close(self):
        self.frame.canvas.close()
        self.toolbar.close()
        super().close()
