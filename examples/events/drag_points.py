"""
Drag points
===========

Example where you can drag scatter points on a line. This example also demonstrates how you can use a shared buffer
between two graphics to represent the same data using different graphics. When you update the data of one graphic the
data of the other graphic is also changed simultaneously since they use the same underlying buffer on the GPU.

"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'screenshot'

import numpy as np
import fastplotlib as fpl
import pygfx

xs = np.linspace(0, 2 * np.pi, 10)
ys = np.sin(xs)

data = np.column_stack([xs, ys])

figure = fpl.Figure(size=(700, 560))

# add a line
line = figure[0, 0].add_line(data)

# add a scatter, share the line graphic buffer!
scatter = figure[0, 0].add_scatter(data=line.data, sizes=25, colors="r")

is_moving = False
vertex_index = None


@scatter.add_event_handler("pointer_down")
def start_drag(ev: pygfx.PointerEvent):
    global is_moving
    global vertex_index

    if ev.button != 1:
        return

    is_moving = True
    vertex_index = ev.pick_info["vertex_index"]
    scatter.colors[vertex_index] = "cyan"


@figure.renderer.add_event_handler("pointer_move")
def move_point(ev):
    global is_moving
    global vertex_index

    # if not moving, return
    if not is_moving:
        return

    # disable controller
    figure[0, 0].controller.enabled = False

    # map x, y from screen space to world space
    pos = figure[0, 0].map_screen_to_world(ev)

    if pos is None:
        # end movement
        is_moving = False
        scatter.colors[vertex_index] = "r"  # reset color
        vertex_index = None
        return

    # change scatter data
    # since we are sharing the buffer, the line data will also change
    scatter.data[vertex_index, :-1] = pos[:-1]

    # re-enable controller
    figure[0, 0].controller.enabled = True


@figure.renderer.add_event_handler("pointer_up")
def end_drag(ev: pygfx.PointerEvent):
    global is_moving
    global vertex_index

    # end movement
    if is_moving:
        # reset color
        scatter.colors[vertex_index] = "r"

    is_moving = False
    vertex_index = None


figure.show()


# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
