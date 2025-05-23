"""
Lineplot Qt
===========

Complex example for lineplot in PyQt that displays 3 traces.
The plot is a standard black on white with a legend on the right.

"""
import sys
import numpy as np
import time
from math import pi, cos, sin, ceil, log10

import fastplotlib as fpl

try:
    from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QMainWindow
    from PyQt6.QtCore import QTimer, Qt

except ImportError:
    from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QMainWindow
    from PyQt5.QtCore import QTimer, Qt

def rotate(angle, axis_x, axis_y, axis_z):
    """
    Quaternion representing rotation around the given axis by the given angle.
    """
    a2 = angle/2.0
    c = cos(a2)
    s = sin(a2)
    return (axis_x * s, axis_y * s, axis_z * s, c)

class FastPlotMain(QMainWindow):

    MAJOR_TICKS = 5
    MINOR_TICKS = 4
    DATAPOINTS  = 5000                   # number of data points per line
    INTERVAL    = 16                     # display refresh in milliseconds
    WHITE       = (1.0, 1.0, 1.0, 1.0)
    BLACK       = (0.0, 0.0, 0.0, 1.0)
    RED         = (1.0, 0.0, 0.0, 1.0)
    GREEN       = (0.0, 1.0, 0.0, 1.0)
    BLUE        = (0.0, 0.0, 1.0, 1.0)
    DARK_GRAY   = (0.2, 0.2, 0.2, 1.0)
    LIGHT_GRAY  = (0.9, 0.9, 0.9, 1.0)

    def __init__(self):
        super().__init__()

        # ─── Window ──────────────────────────────────────────────────────────────
        
        self.setWindowTitle("fastplotlib Line Plot Test")
        self.resize(800, 600)

        # ─── Figure & Subplot ────────────────────────────────────────────────────

        self.fig = fpl.Figure(
            (1, 1),
            size=(800, 600),
            names = "Line Plot",
        )

        # Subplot
        self.ax = self.fig[0, 0]

        # Turn on axi rulers and option grid
        self.ax.axes.visible = True
        self.ax.background_color = self.WHITE
        if self.ax.axes.grids:
            self.ax.axes.grids.xy.visible = True
            self.ax.axes.grids.xy.color   = self.DARK_GRAY

        # ─── Docks: Title & Axis Labels ──────────────────────────────────────────  

        # Title
        self.ax.docks["top"].size = 30
        self.ax.docks["top"].add_text(
            "Line Plots",
            font_size=16,
            face_color=(0, 0, 0, 1),
            anchor="middle-center",
            offset=(0, 0, 0),
        )
        self.ax.docks["top"].background_color = self.WHITE

        # X label
        self.ax.docks["bottom"].size = 30
        self.ax.docks["bottom"].add_text(
            "X",
            font_size=16,
            face_color=(0, 0, 0, 1),
            anchor="middle-center",
            offset=(0, 0, 0),
        )
        self.ax.docks["bottom"].background_color = self.WHITE

        # Y label
        q = rotate(pi/2.0, 0., 0., 1.)  # rotate 90 deg around z-axis
        self.ax.docks["left"].size = 30
        self.ax.docks["left"].add_text(
            "Y",
            font_size=16,
            face_color=(0, 0, 0, 1),
            anchor="middle-center",
            offset=(0, 0, 0),
            rotation=q,
        )
        self.ax.docks["left"].background_color = self.WHITE

        # ─── Data & Graphics ─────────────────────────────────────────────────────

        # Prepare your data buffers
        t = np.linspace(-2*np.pi,2*np.pi,self.DATAPOINTS, dtype = np.float32)
        self.t = t
        self.phase1 = 0.0
        self.phase2 = pi/2.
        N = self.t.size
        self.z = np.zeros_like(self.t, dtype=np.float32)

        # Pre-allocate three (N×3) float32 buffers:
        self.buf1 = np.empty((N, 3), dtype=np.float32)
        self.buf2 = np.empty((N, 3), dtype=np.float32)
        self.buf3 = np.empty((N, 3), dtype=np.float32)

        # Copy the constant x and z columns once:
        self.buf1[:, 0] = self.t;  self.buf1[:, 2] = self.z
        self.buf2[:, 0] = self.t;  self.buf2[:, 2] = self.z
        self.buf3[:, 0] = self.t;  self.buf3[:, 2] = self.z

        # Colors (uniform for all points in a line)
        rgba1 = np.tile(np.array(self.RED,   dtype=np.float32), (self.DATAPOINTS, 1)) # RED
        rgba2 = np.tile(np.array(self.BLACK, dtype=np.float32), (self.DATAPOINTS, 1)) # BLACK
        rgba3 = np.tile(np.array(self.BLUE,  dtype=np.float32), (self.DATAPOINTS, 1)) # BLUE

        # Add the lines to the plot axis
        self.line1 = self.ax.add_line(self.buf1, colors=rgba1)
        self.line2 = self.ax.add_line(self.buf2, colors=rgba2)
        self.line3 = self.ax.add_line(self.buf3, colors=rgba3)

        # ─── View & Axes Ticks ────────────────────────────────────────────────────────   

        self.ax.axes.update_using_camera()
        self.ax.auto_scale(maintain_aspect=True)
        # Zoom
        self.ax.camera.local.scale_x *= 1.0
        self.ax.camera.local.scale_y *= 1.0
        # Draw the axes with ticks
        self.updateAxesTicks(self.ax, self.MAJOR_TICKS, self.MINOR_TICKS)

        # ─── Legend ─────────────────────────────────────────────────────────────
        
        from fastplotlib.legends import Legend
        legend_dock = self.ax.docks["right"]  # options are right, left, top, bottom
        legend_dock.background_color = self.WHITE
        # legend_dock = self.ax  # not working yet, no floating legend on top of plot
        legend_dock.size = 200                # if top/bottom dock that is the height of dock in pixels, 
                                              # if left/right dock that is the width of the dock in pixels,
        self.legend = Legend(
            plot_area=legend_dock,            # the plot area to attach the legend to
            background_color=self.LIGHT_GRAY, # optional: the background color of the legend
            max_rows = 5                      # how many items per column before wrapping
        )
        self.lines = [self.line1, self.line2, self.line3]
        self.labels = ["sin(x)", "rand + 1", "sin(x + θ) - 1"]
        for lg, label in zip(self.lines, self.labels):
            self.legend.add_graphic(lg, label)

        self.legend.update_using_camera()
        
        # ─── Finalize and Show ────────────────────────────────────────────────────

        canvas = self.fig.show(autoscale=True, maintain_aspect=True) # show the figure
        self.setCentralWidget(canvas)
        self.fig.canvas.request_draw()

        # ─── Animation Timer ───────────────────────────────────────────────────

        timer = QTimer(self)
        timer.timeout.connect(self.animate)
        timer.start(self.INTERVAL)

        # ─── One Time Scaling ────────────────────────────────────────────────────────
        # This is to ensure that the plot is at least once autoscaled, otherwise user 
        # sees no plot area

        QTimer.singleShot(
            100,                         # 0 ms → next Qt loop
            self.autoScale               # the slot to call
        )        

        # ─── Benchmark ──────────────────────────────────────────────────────────

        self.last_time = time.perf_counter()
        self.num_segments = 0


    def autoScale(self):
        """Run once, right after the first frame is ready."""
        ax = getattr(self, "ax", None)
        if ax is None:
            return  # nothing to autoscale

        self.ax.auto_scale(maintain_aspect=True, zoom=0.9)
        self.updateAxesTicks(self.ax, self.MAJOR_TICKS, self.MINOR_TICKS)
        self.fig.canvas.request_draw()

    def updateAxesTicks(self, subplot, n_major, n_minor):
        """
        Update the tick marks of the x and y axis.
        """

        # Helper to pick a "nice" power‐of‐10 step and decimal precision
        def nice_step(lo, hi, n):
            rng = (hi - lo) / n
            exp = 0 if rng <= 0 else ceil(log10(rng))
            return 10 ** exp, max(0, -exp)
    
        # Grab world‐space extent from the rulers
        xr, yr = subplot.axes.x, subplot.axes.y

        xmin, _, _ = xr.start_pos
        xmax, _, _ = xr.end_pos
        _, ymin, _ = yr.start_pos
        _, ymax, _ = yr.end_pos

        # Compute the steps
        maj_x, dec_x = nice_step(xmin, xmax, n_major)
        maj_y, dec_y = nice_step(ymin, ymax, n_major)


        # Apply to each ruler
        for r, maj, dec in (
            (xr, maj_x, dec_x), 
            (yr, maj_y, dec_y),
        ):

            r.line.material.color = self.BLACK # Ruler color

            r.major_step = maj                  # Major step
            r.minor_step = maj / n_minor        # Minor step

            r.tick_side = "left" if r is yr else "right" # Tick side
            r.tick_format = f".{dec}f"          # Label format, TODO this is invalid

            if r.ticks is not None:
                r.ticks.material.color = self.BLACK # Major ticks color

            if r.points is not None:
                r.points.material.color = self.BLACK # Major ticks color

            if r.text is not None:
                r.text.material.color = self.BLACK

        if subplot.axes.grids:
            gxy = subplot.axes.grids.xy
            gxy.visible = True                  # Show the grid
            gxy.axis_color = self.BLACK         # Axis color
            gxy.major_color = self.BLACK        # Major grid color
            gxy.minor_color = self.DARK_GRAY    # Minor grid color
            gxy.major_thickness = 1.0           # Major grid thickness
            gxy.minor_thickness = 0.5                # Minor grid thickness

        subplot.axes.update_using_camera() # Update the axes with the new ticks

    def animate(self):

        # Increment phases (animate plots)
        self.phase1 += 0.01  * self.INTERVAL
        self.phase2 += 0.0101 * self.INTERVAL

        # Generate the data

        #   Line 1: sin(t+phase1) in-place
        np.sin(self.t + self.phase1, out=self.buf1[:, 1])

        #   Line 2: rand+1; since rand() has no `out` kwarg, write into buf2[:,1] by slicing:
        self.buf2[:, 1] = np.random.rand(self.t.size).astype(np.float32) + 1.0

        #   Line 3: sin(t+phase2)-1 in-place
        np.sin(self.t + self.phase2, out=self.buf3[:, 1])
        self.buf3[:, 1] -= 1.0

        # Update the data in the plot lines
        self.line1.data = self.buf1
        self.line2.data = self.buf2
        self.line3.data = self.buf3

        # Update the axes
        self.updateAxesTicks(self.ax, self.MAJOR_TICKS, self.MINOR_TICKS)
        
        # Redraw the figure
        self.fig.canvas.request_draw()

        # Benchmark number of segments per second
        self.num_segments += 3 * self.t.size 

        current_time = time.perf_counter()
        if current_time - self.last_time >= 1.0:
            print(f"Segments/s: {self.num_segments}, Segments/Frame: {3*self.t.size}, Frames/s: {1000/(self.INTERVAL):.2f}")
            self.last_time = current_time
            self.num_segments = 0

    def closeEvent(self, ev):
        fpl.loop.stop()
        super().closeEvent(ev)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    # app.setStyle("Fusion")
    # app.setStyleSheet("QWidget { background-color: white; }")
    fpl.loop._app = app

    win = FastPlotMain()
    win.show()

    sys.exit(app.exec())
