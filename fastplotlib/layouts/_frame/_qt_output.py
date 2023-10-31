from PyQt6 import QtWidgets

from ._qt_toolbar import QToolbar


class QOutputContext(QtWidgets.QWidget):
    """
    Output context to display plots in Qt apps. Inherits from QtWidgets.QWidget

    Basically vstacks plot canvas, toolbar, and other widgets.
    """
    def __init__(
            self,
            frame,
            make_toolbar,
            add_widgets,
    ):
        """

        Parameters
        ----------
        frame:
            Plot frame for which to generate the output context

        add_widgets: List[Widget]
            list of QWidget to stack below the plot and toolbar
        """
        # no parent, user can use Plot.widget.setParent(parent) if necessary to embed into other widgets
        QtWidgets.QWidget.__init__(self, parent=None)
        self.frame = frame
        self.toolbar = None

        # vertical layout used to stack plot canvas, toolbar, and add_widgets
        self.vlayout = QtWidgets.QVBoxLayout(self)

        # add canvas to layout
        self.vlayout.addWidget(self.frame.canvas)

        if make_toolbar:  # make toolbar and add to layout
            self.toolbar = QToolbar(output_context=self, plot=frame)
            self.vlayout.addWidget(self.toolbar)

        for w in add_widgets:  # add any additional widgets to layout
            w.setParent(self)
            self.vlayout.addWidget(w)

        self.setLayout(self.vlayout)

        self.resize(*self.frame._starting_size)

        self.show()

    def close(self):
        """Cleanup and close the output context"""
        self.frame.canvas.close()
        self.toolbar.close()
        super().close()  # QWidget cleanup
