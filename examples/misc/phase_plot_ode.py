"""
Phase portrait of ordinary differential equations
=================================================

Very basic example of how to plot the trajectories of a few trajectories that solve an ordinary differential equation
given some constants that help define the starting points
"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'screenshot'

import numpy as np
import scipy

import fastplotlib as fpl


def create_and_solve_ode(
        t_start: float,
        t_end: float,
        n_t: int,
        p: float,
        q: float,
        A: np.ndarray,
        coef: float = 1.0,
) -> float:
    """
    Given an ODE of the form:

    x' = Ax

    where:
    x' ∈ R^2
    x ∈ R^2, x is a function of x, i.e. x(t)
    A ∈ R^2x2

    We can solve this ODE through an eigendecomposition of A:

    A η_i = λ_i η_i

    where λ_i, η_i are the eigenvalues and eigenvectors of A.

    Thus this gives us the following solution for x(t):

    x(t) = p * η_1 * e^(λ_1 * t) + q * η_2 * e^(λ_2 * t)

    where p and q are constants that determine the initial conditions

    Parameters
    ----------
    t_start: float
    t_end: float
    p: float
    q: float
    A: np.ndarray
    coef: float

    Returns
    -------

    np.ndarray

    """

    matrix = A * np.array([[1, 1], [1 / coef, 1 / coef]])

    (lam1, lam2), evecs = scipy.linalg.eig(matrix)
    eta1 = evecs[:, 0]
    eta2 = evecs[:, 1]

    x_t = np.zeros((n_t, 2))

    for i, t in enumerate(np.linspace(t_start, t_end, n_t)):
        x_t[i] = (p * eta1 * np.exp(lam1 * t)) + (q * eta2 * np.exp(lam2 * t))

    return x_t


# constants range
START, STOP = -2, 2

T_START, T_END = -2, 5

A = np.array([
    [0, 1],
    [-1, -1]
])

x_t_collection = list()
x_t_vel_collection = list()

for p in np.linspace(START, STOP, 8):
    for q in np.linspace(START, STOP, 8):
        n_t = 100

        x_t_vel = np.zeros(n_t)

        x_t = create_and_solve_ode(
            t_start=T_START,
            t_end=T_END,
            n_t=n_t,
            p=p,
            q=q,
            A=A,
            coef=0.5,
        )

        x_t_vel[:-1] = np.linalg.norm(x_t[:-1] - x_t[1:], axis=1, ord=2)
        x_t_vel[-1] = x_t_vel[-2]

        x_t_collection.append(x_t)
        x_t_vel_collection.append(x_t_vel)

fig = fpl.Figure()

lines = fig[0, 0].add_line_collection(x_t_collection, cmap="viridis", cmap_transform=x_t_vel_collection)
for (line, vel) in zip(lines, x_t_vel_collection):
    line.cmap = "viridis"

    # color indicates velocity along trajectory
    line.cmap.transform = vel
    print(vel)

fig[0, 0].axes.intersection = (0, 0, 0)

fig.show()

# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# please see our docs for using fastplotlib interactively in ipython and jupyter
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
