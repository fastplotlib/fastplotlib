"""
Drag points
===========

Example where you can drag points along a line. This example also demonstrates how you can use a shared buffer
between two graphics to represent the same data using different graphics. When you update the data of one graphic the
data of the other graphic is also changed simultaneously since they use the same underlying buffer on the GPU.

"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'.

import numpy as np
import fastplotlib as fpl
import pygfx

xs = np.linspace(0, 2 * np.pi, 10)
ys = np.sin(xs)

data = np.column_stack([xs, ys])

figure = fpl.Figure()

# add a line
line_graphic = figure[0, 0].add_line(data)

# add a scatter, share the line graphic buffer!
scatter_graphic = figure[0, 0].add_scatter(data=line_graphic.data, sizes=20, colors="r")

is_moving = False
vertex_index = None


@scatter_graphic.add_event_handler("pointer_down", "pointer_up", "pointer_move")
def toggle_drag(ev: pygfx.PointerEvent):
    global is_moving
    global vertex_index

    if ev.type == "pointer_down":
        if ev.button != 1:
            return

        is_moving = True
        vertex_index = ev.pick_info["vertex_index"]

    elif ev.type == "pointer_up":
        is_moving = False


@figure.renderer.add_event_handler("pointer_move")
def move_point(ev):
    global is_moving
    global vertex_index

    if not is_moving:
        vertex_index = None
        return

    # disable controller
    figure[0, 0].controller.enabled = False

    # map x, y from screen space to world space
    pos = figure[0, 0].map_screen_to_world(ev)[:-1]

    # change scatter data
    # since we are sharing the buffer, the line data will also change
    scatter_graphic.data[vertex_index, :-1] = pos

    # re-enable controller
    figure[0, 0].controller.enabled = True


figure.show()


# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# please see our docs for using fastplotlib interactively in ipython and jupyter
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
