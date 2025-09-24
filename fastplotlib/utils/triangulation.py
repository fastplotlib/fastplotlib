import logging

import numpy as np
from .mapbox_earcut import earcut as mapbox_earcut


logger = logging.getLogger("fastplotlib")


# Note: the current triangulation is in pure Python. If the results or performance of the current implementation
# proves inadequate, we can have a look at Bermuda: https://github.com/napari/bermuda


def triangulate(positions, method="earcut"):
    """Triangulate the given vertex positions.

    Returns an Nx3 integer array of faces that form a surface-mesh over the
    given positions, where N is the length of the positions minus 2,
    expressed in (local) vertex indices. The faces won't contain any
    forbidden_edges.
    """
    if len(positions) < 3:
        return np.zeros((0,), np.int32)
    if len(positions) == 3:
        return np.array([0, 1, 2], np.int32)

    # Anticipating more variations ...
    if method == "earcut":
        method = "mapbox_earcut"

    if method == "naive":
        faces = _triangulate_naive(positions)
    elif method == "mapbox_earcut":
        positions2d = positions[:, :2].flatten()
        faces = mapbox_earcut(positions2d)
        faces = np.array(faces, np.int32).reshape(-1, 3)
    else:
        raise ValueError(f"Invalid triangulation method: {method}")

    return faces


def _triangulate_naive(positions, forbidden_edges=None):
    """This tesselation algorithm simply creates edges from one vertex to all the others."""

    nverts = len(positions)
    nfaces = nverts - 2
    forbidden_edges = forbidden_edges or []

    # Determine a good point to be a reference
    forbidden_start_points = set()
    for i1, i2 in forbidden_edges:
        forbidden_start_points.add(i1)
        forbidden_start_points.add(i2)
    for i in range(len(positions)):
        if i not in forbidden_start_points:
            start_point = i
            break
    else:
        # In real meshes this cannot happen, but it can from the POV of this function's API
        raise RuntimeError("Cannot tesselate.")

    # Collect the faces
    faces = []
    i0 = start_point
    for i in range(start_point, start_point + nfaces):
        i1 = (i + 1) % nverts
        i2 = (i + 2) % nverts
        faces.append([i0, i1, i2])
    return np.array(faces, np.int32)
