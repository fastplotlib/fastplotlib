from typing import Sequence

import pygfx
from pygfx.geometries.utils import merge as merge_geometries
import pylinalg as la
import numpy as np

from ._base import Graphic
from .features import (
    VectorPositions,
    VectorDirections,
)


class VectorField(Graphic):
    _features = {
        "positions": VectorPositions,
        "directions": VectorDirections,
    }

    def __init__(
        self,
        positions: np.ndarray | Sequence[float],
        directions: np.ndarray | Sequence[float],
        color: str | Sequence[float] | np.ndarray = "w",
        size: float = None,
        vector_shape_options: dict = None,
        **kwargs,
    ):
        """
        Create a Vector Field. Similar to matplotlib quiver.

        Parameters
        ----------
        positions: np.ndarray | Sequence[float]
            positions of the vectors, array-like, shape must be [n, 2] or [n, 3] where n is the number of vectors.

        directions: np.ndarray | Sequence[float]
            directions of the vectors, array-like, shape must be [n, 2] or [n, 3] where n is the number of vectors.

        spacing: float
            average distance between pairs of nearest-neighbor vectors, used for scaling

        color: str | pygfx.Color | Sequence[float] | np.ndarray, default "w"
            color of the vectors

        size: float or None
            Size of a vector of magnitude 1 in world space for display purpose.
            Estimated from field density if not provided.

        vector_shape_options: dict
            dict with the following fields that directly describes the shape of the vector arrows.
            Overrides ``size`` argument.


                * cone_radius
                * cone_height
                * stalk_radius
                * stalk_height

        **kwargs
            passed to :class:`.Graphic`

        """

        super().__init__(**kwargs)

        self._positions = VectorPositions(positions)
        self._directions = VectorDirections(directions)

        if size is None and vector_shape_options is None:
            # guess from field density

            # sort xs and then take unique to get the density along x, same for y and z
            x_density = np.diff(np.unique(np.sort(positions[:, 0]))).mean()
            y_density = np.diff(np.unique(np.sort(positions[:, 1]))).mean()
            densities = [x_density, y_density]

            if positions.shape[1] == 3:
                z_density = np.diff(np.unique(np.sort(positions[:, 2]))).mean()
                densities.append(z_density)
            print(densities)
            mean_density = np.mean(densities)

            size = mean_density

            cone_height = size / 2
            stalk_height = size / 2

            cone_radius = size / 10
            stalk_radius = cone_radius / 8

            shape_options = {
                "cone_radius": cone_radius,
                "cone_height": cone_height,
                "stalk_radius": stalk_radius,
                "stalk_height": stalk_height,
            }

        # if vector_shape_options is None:
        #     vector_shape_options = {}
        #
        # for k in vector_shape_options:
        #     if k not in shape_options:
        #         raise KeyError(
        #             f"valid dict fields for `vector_shape_options` are: {list(shape_options.keys())}. "
        #             f"You passed the following dict: {vector_shape_options}"
        #         )

        geometry = create_vector_geometry(color=color, **shape_options)
        material = pygfx.MeshBasicMaterial()

        n_vectors = self._positions.value.shape[0]

        world_object = pygfx.InstancedMesh(geometry, material, n_vectors)

        magnitudes = np.linalg.norm(self.directions[:], axis=1, ord=2)

        start_rot = np.array([0, 0, 1])

        for i in range(n_vectors):
            # get quaternion to rotate existing vector direction to new direction
            rotation = la.quat_from_vecs(start_rot, self._directions[i])
            # get the new transform
            transform = la.mat_compose(
                self._positions.value[i], rotation, magnitudes[i]
            )
            # set the buffer
            world_object.instance_buffer.data["matrix"][i] = transform.T

        world_object.instance_buffer.update_full()

        self._set_world_object(world_object)

    @property
    def positions(self) -> VectorPositions:
        """Vector positions"""
        return self._positions

    @positions.setter
    def positions(self, new_positions):
        self._positions.set_value(self, new_positions)

    @property
    def directions(self) -> VectorDirections:
        """Vector directions"""
        return self._directions

    @directions.setter
    def directions(self, new_directions):
        self._directions.set_value(self, new_directions)


# mesh code copied and adapted from pygfx
def generate_torso(
    radius_bottom,
    radius_top,
    height,
    radial_segments,
    height_segments,
    theta_start,
    theta_length,
    z_offset=0.0,
):
    # compute POSITIONS assuming x-y horizontal plane and z up axis

    # radius for each vertex ring from bottom to top
    n_rings = height_segments + 1
    radii = np.linspace(radius_bottom, radius_top, num=n_rings, dtype=np.float32)

    # height for each vertex ring from bottom to top
    half_height = height / 2
    heights = np.linspace(-half_height, half_height, num=n_rings, dtype=np.float32)

    # to enable texture mapping to fully wrap around the cylinder,
    # we can't close the geometry and need a degenerate vertex
    n_vertices = radial_segments + 1

    # xy coordinates on unit circle for a single vertex ring
    theta = np.linspace(
        theta_start, theta_start + theta_length, num=n_vertices, dtype=np.float32
    )
    ring_xy = np.column_stack([np.cos(theta), np.sin(theta)])

    # put all the rings together
    positions = np.empty((n_rings, n_vertices, 3), dtype=np.float32)
    positions[..., :2] = ring_xy[None, ...] * radii[:, None, None]
    positions[..., 2] = heights[:, None] - z_offset

    # the NORMALS are the same for every ring, so compute for only one ring
    # and then repeat
    slope = (radius_bottom - radius_top) / height
    ring_normals = np.empty(positions.shape[1:], dtype=np.float32)
    ring_normals[..., :2] = ring_xy
    ring_normals[..., 2] = slope
    ring_normals /= np.linalg.norm(ring_normals, axis=-1)[:, None]
    normals = np.empty_like(positions)
    normals[:] = ring_normals[None, ...]

    # the TEXTURE COORDS
    # u maps 0..1 to theta_start..theta_start+theta_length
    # v maps 0..1 to -height/2..height/2
    ring_u = (theta - theta_start) / theta_length
    ring_v = (heights / height) + 0.5
    texcoords = np.empty((n_rings, n_vertices, 2), dtype=np.float32)
    texcoords[..., 0] = ring_u[None, :]
    texcoords[..., 1] = ring_v[:, None]

    # the face INDEX
    # the amount of vertices
    indices = np.arange(n_rings * n_vertices, dtype=np.uint32).reshape(
        (n_rings, n_vertices)
    )
    # for every panel (height_segments, radial_segments) there is a quad (2, 3)
    index = np.empty((height_segments, radial_segments, 2, 3), dtype=np.uint32)
    # create a grid of initial indices for the panels
    index[:, :, 0, 0] = indices[
        np.arange(height_segments)[:, None], np.arange(radial_segments)[None, :]
    ]
    # the remainder of the indices for every panel are relative
    index[:, :, 0, 1] = index[:, :, 0, 0] + 1
    index[:, :, 0, 2] = index[:, :, 0, 0] + n_vertices
    index[:, :, 1, 0] = index[:, :, 0, 0] + n_vertices + 1
    index[:, :, 1, 1] = index[:, :, 1, 0] - 1
    index[:, :, 1, 2] = index[:, :, 1, 0] - n_vertices

    return (
        positions.reshape((-1, 3)),
        normals.reshape((-1, 3)),
        texcoords.reshape((-1, 2)),
        index.flatten(),
    )


def generate_cap(radius, height, radial_segments, theta_start, theta_length, up=True):
    # compute POSITIONS assuming x-y horizontal plane and z up axis

    # to enable texture mapping to fully wrap around the cylinder,
    # we can't close the geometry and need a degenerate vertex
    n_vertices = radial_segments + 1

    # xy coordinates on unit circle for vertex ring
    theta = np.linspace(
        theta_start, theta_start + theta_length, num=n_vertices, dtype=np.float32
    )
    ring_xy = np.column_stack([np.cos(theta), np.sin(theta)])

    # put the vertices together, inserting a center vertex at the start
    positions = np.empty((1 + n_vertices, 3), dtype=np.float32)
    positions[0, :2] = [0.0, 0.0]
    positions[1:, :2] = ring_xy * radius
    positions[..., 2] = height

    # the NORMALS
    normals = np.zeros_like(positions, dtype=np.float32)
    sign = int(up) * 2.0 - 1.0
    normals[..., 2] = sign

    # the TEXTURE COORDS
    # uv etches out a circle from the [0..1, 0..1] range
    # direction is reversed for up=False
    texcoords = np.empty((1 + n_vertices, 2), dtype=np.float32)
    texcoords[0] = [0.5, 0.5]
    texcoords[1:, 0] = ring_xy[:, 0] * 0.5 + 0.5
    texcoords[1:, 1] = ring_xy[:, 1] * 0.5 * sign + 0.5

    # the face INDEX
    indices = np.arange(n_vertices) + 1
    # for every radial segment there is a triangle (3)
    index = np.empty((radial_segments, 3), dtype=np.uint32)
    # create a grid of initial indices for the panels
    index[:, 0] = indices[np.arange(radial_segments)]
    # the remainder of the indices for every panel are relative
    index[:, 1 + int(up)] = n_vertices
    index[:, 2 - int(up)] = index[:, 0] + 1

    return (
        positions,
        normals,
        texcoords,
        index.flatten(),
    )


def create_vector_geometry(
    color: str | pygfx.Color | Sequence[float] | np.ndarray = "w",
    cone_cap_color: str | pygfx.Color | Sequence[float] | np.ndarray | None = None,
    cone_radius: float = 10.0,
    cone_height: float = 4.0,
    stalk_radius: float = 30.0,
    stalk_height: float = 4.0,
    segments: int = 24,
):
    radius_top = 0

    radial_segments = segments

    height_segments = 1
    theta_start = 0.0
    theta_length = np.pi * 2

    # create cone
    cone = generate_torso(
        cone_radius,
        radius_top,
        cone_height,
        radial_segments,
        height_segments,
        theta_start,
        theta_length,
    )

    groups = [cone]

    cone_cap_start_ix = len(cone[0])

    # create bottom cap
    cone_cap = generate_cap(
        cone_radius,
        -cone_height / 2,
        radial_segments,
        theta_start,
        theta_length,
        up=False,
    )

    cone_cap_stop_ix = cone_cap_start_ix + len(cone_cap[0])

    groups.append(cone_cap)

    stalk = generate_torso(
        stalk_radius,
        stalk_radius,
        stalk_height,
        radial_segments,
        height_segments,
        theta_start,
        theta_length,
        z_offset=cone_height,
    )

    groups.append(stalk)

    stalk_cap = generate_cap(
        stalk_radius,
        -stalk_radius / 2,
        radial_segments,
        theta_start,
        theta_length,
        up=False,
    )

    groups.append(stalk_cap)

    merged = merge_geometries(groups)

    positions, normals, texcoords, indices = merged

    color = np.array(pygfx.Color(color).rgb, dtype=np.float32)

    # color the cone cap in a different color
    if cone_cap_color is not None:
        cone_cap_color = np.array(pygfx.Color(cone_cap_color).rgb, dtype=np.float32)
    else:
        # make the cone cap a slightly darker version of the cone color
        cone_cap_color = (color - np.array([0.25, 0.25, 0.25], dtype=np.float32)).clip(
            0
        )

    colors = np.repeat([color], repeats=len(positions), axis=0)

    colors[cone_cap_start_ix:cone_cap_stop_ix, :] = cone_cap_color

    return pygfx.Geometry(
        indices=indices.reshape((-1, 3)),
        positions=positions,
        normals=normals,
        texcoords=texcoords,
        colors=colors,
    )
