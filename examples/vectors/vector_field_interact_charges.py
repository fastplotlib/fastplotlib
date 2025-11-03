"""
View Electric Field
===================

Interactively move the charges around by clicking and dragging the mouse to see
the static field with the charges at their new positions. This is just computing
static fields, no electrodynamics or magnetic field effects are taken into account.

"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'screenshot'

import numpy as np
import fastplotlib as fpl
import pygfx


# based on vacuum permittivity, 1/4πε from wikipedia: https://en.wikipedia.org/wiki/Coulomb%27s_law#Coulomb_constant
k_e = 8.98755 * 10**9


def coulombs_law(q: float, r: np.ndarray) -> np.ndarray[float, float]:
    """
    Compute force on a unit charge at a distance ``r`` from a particle of charge ``q``.
    Broadcasts over ``r`` array.

    q: charge in coulombs
    r: 2D array of distance vectors, shape [n, 2]

    Returns force vector at each distance ``r`` provided, shape [n, 2]
    """
    r_cap = r / np.linalg.norm(r, ord=2, axis=1)[:, None]
    F = k_e * ((q * r_cap) / ((np.linalg.norm(r, ord=2, axis=1))**2)[:, None])

    return F


figure = fpl.Figure(size=(700, 750))

# positions of 3 particles, ignore z
positions = np.array([
    [3, 3, 0],
    [8, 5, 0],
    [4, 8, 0],
])

# charges of the 3 particles
charges = np.array([
    3.5 * 10**-10,
    1 * 10**-10,
    -3.5 * 10**-10,
])

# red to indicate positive charge, blue to indicate negative charge
colors = ["r", "r", "b"]

# scatter point to indicate particle positions
particles = figure[0, 0].add_scatter(
    data=positions,
    colors=colors,
    sizes=1,
    edge_width=0.05,
    uniform_edge_color=False,
    alpha=0.7,
    size_space="model",
    metadata={"charges": charges},  # you can store anything as arbitrary metadata
    alpha_mode="blend",
)

xs = np.linspace(0, 10, num=20)
ys = np.linspace(0, 10, num=20)

x, y = np.meshgrid(xs, ys)

# display vectors at these positions in the field
field_positions = np.column_stack([x.ravel(), y.ravel()])

# direction of the field at every position due to the particle's charge
# i.e., the force felt by a unit charge at a given position in the field
field_directions = np.ones(field_positions.shape, dtype=np.float32)

vectors = figure[0, 0].add_vectors(
    positions=field_positions,
    directions=field_directions,
    alpha=0.7,
    alpha_mode="blend",
)


def update_field():
    """update the static field w.r.t. the new positions of the particles"""

    # get force vectors due to each charge and add them up
    force_vectors_total = np.zeros(field_positions.shape)

    for i in range(particles.data.value.shape[0]):
        force_vectors = coulombs_law(
            q=particles.metadata["charges"][i],  # force due to one of the charges
            r=field_positions - particles.data[:, :-1][i]
        )

        force_vectors_total = force_vectors_total + force_vectors

    # zero out when the force is too large to display
    # large vectors will otherwise take up the entire plot area
    force_vectors_total[np.linalg.norm(force_vectors_total, axis=1, ord=2) > 3.5] = 0

    # update the graphic
    vectors.directions = force_vectors_total


update_field()

# render particles on top of field
particles.world_object.material.render_queue = vectors.world_object.material.render_queue + 1

# interactivity code, very similar to the "Drag points" example
is_moving = False
particle_index = None
# interact with particles by moving them with mouse
@particles.add_event_handler("pointer_down")
def start_drag(ev: pygfx.PointerEvent):
    global is_moving
    global particle_index

    if ev.button != 1:  # check for left mouse button
        return

    is_moving = True
    particle_index = ev.pick_info["vertex_index"]
    # set edge color to indicate this particle has been selected
    particles.edge_colors[particle_index] = "y"


@figure.renderer.add_event_handler("pointer_move")
def move_point(ev):
    global is_moving
    global particle_index

    # if not moving, return
    if not is_moving:
        return

    # pause controller so mouse events move the scatter and not the camera
    with figure[0, 0].controller.pause():
        # map x, y from screen space to world space
        pos = figure[0, 0].map_screen_to_world(ev)

        if pos is None:
            # end movement
            is_moving = False
            particle_index = None
            return

        # change scatter data
        particles.data[particle_index, :-1] = pos[:-1]
        # update field
        update_field()


@figure.renderer.add_event_handler("pointer_up")
def end_drag(ev: pygfx.PointerEvent):
    global is_moving
    global particle_index

    # end movement
    if is_moving:
        # reset color
        particles.edge_colors[particle_index] = "k"

    is_moving = False
    particle_index = None


figure.show()

# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
