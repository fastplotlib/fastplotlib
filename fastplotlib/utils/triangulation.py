import logging

import numpy as np


logger = logging.getLogger("fastplotlib")


def triangulate(positions, forbidden_edges=None, method="earcut"):
    """Triangulate the given vertex positions.

    Returns an Nx3 integer array of faces that form a surface-mesh over the
    given positions, where N is the length of the positions minus 2,
    expressed in (local) vertex indices. The faces won't contain any
    forbidden_edges.
    """
    forbidden_edges = forbidden_edges or []

    # Anticipating more variations ...
    if method == "earcut":
        method = "earcut1"

    if method == "naive":
        faces = _triangulate_naive(positions, forbidden_edges, method)
    elif method == "earcut1":
        try:
            faces = _triangulate_earcut1(positions, forbidden_edges, method)
        except RuntimeError as err:
            # I think this should not happen, but if I'm wrong, we still produce a result
            logger.warning(str(err))
            faces = _triangulate_naive(positions, forbidden_edges, method)
    else:
        raise ValueError(f"Invalid triangulation method: {method}")

    # Check result
    nverts = len(positions)
    nfaces = nverts - 2
    assert len(faces) == nfaces

    return faces


def _triangulate_naive(positions, forbidden_edges, method):
    """This tesselation algorithm simply creates edges from one vertex to all the others."""

    nverts = len(positions)
    nfaces = nverts - 2

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


def _triangulate_earcut1(positions, forbidden_edges, method, ref_normal=None):
    """This tesselation algorithm uses the earcut algorithm plus some
    other features to iteratively create faces.
    """

    # This code is originally from https://github.com/pygfx/gfxmorph/blob/main/gfxmorph/meshfuncs.py
    # For now I just copied the implementation.

    # Generate new faces, using the contour as a kind of circular queue.
    # We will pop vertices from the queue as we "cut ears off the
    # polygon", and as such the contour will become smaller until we
    # are left with a triangle. At the last step, when we have a quad,
    # we need to take care to take the symmetry into account.
    #
    # Check all three consecutive vertices, and select the best ear.
    # How to do this matters for the eventual result, also because
    # selecting a particular ear affects the shape of the remaining
    # hole.
    #
    # We want to avoid faces "folding over", prefer more or less equal
    # edge lengths, and pick in such an order that in the last step we
    # don't have a crap quad. There is a multitude of possible
    # algorithms here. In our case we don't necessarily need the best
    # solution since we have a rather iterative (and interactive)
    # setting.
    #
    # Favoring one of the two side-vertices to be close to the contour
    # center seems to work well, since it quickly triangulates vertices
    # that come inwards and which may otherwise cause slither faces.
    # It also promotes faces with good aspect ratio, which is also
    # emphasised by scaling the score with the distance to the center.
    # This score works considerably better than scoring on aspect ratio
    # directly. I think this is because it promotes a better order in
    # which ears are cut from the contour.
    #
    # Although this method helps prevent folded faces, it does not
    # guarantee their absence.

    new_faces = []
    qq = list(range(len(positions)))

    while len(qq) > 3:
        # Calculate center of the current hole
        center = positions[qq].sum(axis=0) / len(qq)

        # Get distance of all points to the center
        distances = np.linalg.norm(center - positions[qq], axis=1)

        is_quad = len(qq) == 4
        n_iters = 2 if is_quad else len(qq)
        best_i = best_ear = -1
        best_score = -999999999999

        for i in range(n_iters):
            # Get indices of "side vertices", and the actual vertex indices
            i1 = i - 1
            i2 = i + 1
            if i == 0:
                i1 = len(qq) - 1
            elif i == len(qq) - 1:
                i2 = 0
            q1, q0, q2 = qq[i1], qq[i], qq[i2]

            # Is this triangle allowed?
            if (q1, q2) in forbidden_edges:
                continue

            # Get distance of reference vertex to the center. Using the
            # plain distance works, but using the distance from the
            # edge better prevents folded faces.
            # d_factor = distances[i]
            d_factor = distance_of_point_to_line_piece(
                positions[q0], positions[q1], positions[q2]
            )
            if is_quad:
                # If we're considering a quad, we must take symmetry
                # into account; the best score might actually be the
                # worst score when viewed from the opposite end.
                # d_alt = distances[i + 2]
                d_alt = distance_of_point_to_line_piece(
                    positions[qq[i + 2]], positions[q2], positions[q1]
                )
                d_factor = min(d_factor, d_alt)
            # Get score and see if it's the best so far
            this_score = d_factor / max(1e-9, min(distances[i1], distances[i2]))
            if this_score > best_score:
                best_score = this_score
                best_ear = q1, q0, q2
                best_i = i

        # I *think* that as long as the mesh is manifold, there is
        # always a solution, because if one of the edges in the final
        # quad is forbidden, the other edge cannot be. But just in case,
        # we cover the case where we did not find a solution.
        if best_i < 0:
            raise RuntimeError("Could not tesselate!")

        # Register new face and reduce the contour
        new_faces.append(best_ear)
        qq.pop(best_i)

    # Only a triangle left. Add the final face - not much to choose
    assert len(qq) == 3
    new_faces.append((qq[0], qq[1], qq[2]))

    return np.array(new_faces, np.int32)


def distance_of_point_to_line_piece(p1, p2, p3):
    """Calculate the distance of point p1 to the line-piece p2-p3."""
    # Also http://mathworld.wolfram.com/Point-LineDistance3-Dimensional.html
    # We make use of two ways to calculate the area. One is Heron's formula,
    # the other is 0.5 * b * h, where b is the length of the linepiece and h
    # is our distance.
    norm = np.linalg.norm
    d12 = norm(p1 - p2)
    d23 = norm(p2 - p3)
    d31 = norm(p3 - p1)
    s = (d12 + d23 + d31) / 2  # semiperimiter
    b = d23
    area = (s * (s - d12) * (s - d23) * (s - d31)) ** 0.5  # Herons formula
    h = area * 2 / b  # area = b * h / 2  -->  h = area * 2 / b
    # Is p1 beyond one of the end-points? If so, return distance to closest point.
    max_dist = (h * h + b * b) ** 0.5
    if max(d12, d31) > max_dist:
        return min(d12, d31)
    else:
        return h
