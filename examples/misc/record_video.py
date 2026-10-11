"""
Record Video
============

Example showing how to record a Figure to a video file. The recording includes everything
drawn in the canvas, including the toolbar and any other UI.

Recording can also be started and stopped with the record button in the subplot toolbar.
Videos are saved as ``fastplotlib_<date>_<time>.mp4`` in the current working directory
unless a ``path`` is given. Recording requires ``av``: ``pip install av``
"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'code'

import fastplotlib as fpl
import numpy as np

# number of frames to record
n_frames = 300

xs = np.linspace(0, 4 * np.pi, 200)
ys = np.sin(xs)

figure = fpl.Figure(size=(700, 560))

sine = figure[0, 0].add_line(np.column_stack([xs, ys]), thickness=5, cmap="viridis")

i = 0
def update_line(subplot):
    global i

    # shift the sine wave
    sine.data[:, 1] = np.sin(xs + i * 0.05)

    # stop recording after n_frames, the video file is saved when recording stops
    i += 1
    if i == n_frames:
        figure.stop_recording()

figure[0, 0].add_animations(update_line)

figure.show()

# start recording, every rendered frame is written to the video until stop_recording() is called
figure.start_recording("sine_wave.mp4")


# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()