import numpy as np
import fastplotlib as fpl
from fastplotlib.ui import DebugWindow
import pygfx
from icecream import ic

xs = np.linspace(0, 10 * np.pi, 1000)
ys = np.sin(xs)

ys100 = ys * 1000

l1 = np.column_stack([xs, ys])
l2 = np.column_stack([xs, ys100])

fig = fpl.Figure(size=(500, 400))

fig[0, 0].add_line(l1)
fig.show(maintain_aspect=False)
fig[0, 0].auto_scale(zoom=0.4)

rs = fig[0, 0].add_reference_frame(
    scale=(1, 500, 1),
)
l2 = fig[0, 0].add_line(l2, reference_space=rs, colors="r")
l2.add_axes(rs)
l2.axes.y.line.material.color = "m"


@fig.renderer.add_event_handler("key_down")
def change_y_scale(ev: pygfx.KeyboardEvent):
    if ev.key != "1":
        return

    rs.controller.remove_camera(rs.camera)
    rs.controller.add_camera(rs.camera, include_state={"height"})

    fig[0, 0].controller.enabled = False


@fig.renderer.add_event_handler("key_down")
def change_y_scale(ev: pygfx.KeyboardEvent):
    if ev.key != "0":
        return

    rs.controller.remove_camera(rs.camera)
    rs.controller.add_camera(rs.camera)
    fig[0, 0].controller.enabled = True


debug_objs = [
    fig[0, 0].camera.get_state,
    rs.camera.get_state
]

debug_window = DebugWindow(debug_objs)
fig.add_gui(debug_window)


fpl.loop.run()
