import numpy as np
import pylinalg as la

from ._base import (
    GraphicFeature,
    GraphicFeatureEvent,
    block_reentrance,
)


# it doesn't make sense to modify just a portion of a vector field, I can't think of a use case.
# so we only allow setting the entire buffer, but allow getting portions of it
class VectorPositions(GraphicFeature):
    event_info_spec = [
        {
            "dict key": "value",
            "type": "np.ndarray",
            "description": "new vector positions",
        },
    ]

    def __init__(
        self,
        positions: np.ndarray,
        property_name: str = "positions",
    ):
        """
        Manages vector field positions by managing the translation elements of the mesh instance transform matrix buffer
        """

        positions = np.asarray(positions, dtype=np.float32)
        if positions.ndim != 2:
            raise ValueError(
                f"vector field positions must be of shape [n, 2] or [n, 3]"
            )

        if positions.shape[1] == 2:
            positions = np.column_stack(
                [
                    positions[:, 0],
                    positions[:, 1],
                    np.zeros(positions.shape[0], dtype=np.float32),
                ]
            )

        elif positions.shape[1] == 3:
            pass

        else:
            raise ValueError(
                f"vector field positions must be of shape [n, 2] or [n, 3]"
            )

        self._positions = positions

        super().__init__(property_name=property_name)

    @property
    def value(self) -> np.ndarray:
        return self._positions

    def __getitem__(self, item):
        return self.value[item]

    def __setitem__(self, key, value):
        raise NotImplementedError(
            "cannot set individual slices of vector positions, must set all positions"
        )

    @block_reentrance
    def set_value(self, graphic, value: np.ndarray):
        if value.shape[0] != self._positions.shape[0]:
            raise ValueError(
                f"number of vector positions in passed array != number of vectors in graphic: "
                f"{value.shape[0]} != {self._positions.shape[0]}"
            )

        if value.shape[1] == 2:
            # assume 2d
            self._positions[:, :-1] = value

        else:
            self._positions[:] = value

        # Only need to update the translation vector
        graphic.world_object.instance_buffer.data["matrix"][:, 3, 0:3] = self._positions[:]

        graphic.world_object.instance_buffer.update_full()

        event = GraphicFeatureEvent(type="positions", info={"value": value})
        self._call_event_handlers(event)


class VectorDirections(GraphicFeature):
    event_info_spec = [
        {
            "dict key": "value",
            "type": "np.ndarray",
            "description": "new vector directions",
        },
    ]

    # vector is always pointing in [0, 0, 1] when mesh is initialized
    init_direction = np.array([0, 0, 1])
    init_direction.flags.writeable = False

    def __init__(
        self,
        directions: np.ndarray,
        property_name: str = "directions",
    ):
        """Manages vector field positions by managing the mesh instance buffer's full transform matrix"""

        directions = np.asarray(directions, dtype=np.float32)
        if directions.ndim != 2:
            raise ValueError(
                f"vector field directions must be of shape [n, 2] or [n, 3]"
            )

        if directions.shape[1] == 2:
            directions = np.column_stack(
                [
                    directions[:, 0],
                    directions[:, 1],
                    np.zeros(directions.shape[0], dtype=np.float32),
                ]
            )

        elif directions.shape[1] == 3:
            pass

        else:
            raise ValueError(
                f"vector field directions must be of shape [n, 2] or [n, 3]"
            )

        self._directions = directions

        super().__init__(property_name=property_name)

    @property
    def value(self) -> np.ndarray:
        return self._directions

    def __getitem__(self, item):
        return self.value[item]

    def __setitem__(self, key, value):
        raise NotImplementedError(
            "cannot set individual slices of vector directions, must set all directions"
        )

    @block_reentrance
    def set_value(self, graphic, value: np.ndarray):
        if value.shape[0] != self._directions.shape[0]:
            raise ValueError(
                f"number of vector directions in passed array != number of vectors in graphic: "
                f"{value.shape[0]} != {self._directions.shape[0]}"
            )

        if value.shape[1] == 2:
            # assume 2d
            self._directions[:, :-1] = value

        else:
            self._directions[:] = value

        # vector determines the size of the vector
        magnitudes = np.linalg.norm(self._directions, axis=1, ord=2)

        # for i in range(self._directions.shape[0]):
            # get quaternion to rotate vector to new direction
        rotation = quat_from_vecs(self.init_direction, self._directions[:])
        # get the new transform
        transform = mat_compose(graphic.positions[:], rotation, magnitudes[:])
        # set the buffer
        graphic.world_object.instance_buffer.data["matrix"][:] = transform.transpose(0, 2, 1)

        graphic.world_object.instance_buffer.update_full()

        event = GraphicFeatureEvent(type="directions", info={"value": value})
        self._call_event_handlers(event)



def quat_from_vecs(source, target, out=None, dtype=None) -> np.ndarray:
    source = np.asarray(source, dtype=float)
    if source.ndim == 1:
        source = source[None, :]
    target = np.asarray(target, dtype=float)
    if target.ndim == 1:
        target = target[None, :]

    num_vecs = target.shape[0]
    result_shape = (num_vecs, 4)
    if out is None:
        out = np.empty(result_shape, dtype=dtype)

    axis = np.cross(source, target)  # (num_pts, 3)
    axis_norm = np.linalg.norm(axis, axis=-1)  # (num_pts,)
    angle = np.arctan2(axis_norm, np.sum(source * target, axis=-1))  # (num_pts,)

    # Handle degenerate case: source and target are parallel (axis is zero vector).
    # Pick any axis orthogonal to source as a replacement.
    use_fallback = axis_norm == 0
    if np.any(use_fallback):
        t = np.broadcast_to(source, (num_vecs, 3))[use_fallback]

        # Better case split:
        y_zero = t[:, 1] == 0
        z_zero = t[:, 2] == 0
        neither_zero = ~y_zero & ~z_zero

        fb = np.empty((y_zero.shape[0], 3), dtype=float)
        fb[y_zero]      = (0., 1., 0.)
        fb[~y_zero & z_zero] = (0., 0., 1.)
        fb[neither_zero, 0] =  0.
        fb[neither_zero, 1] = -t[neither_zero, 2]
        fb[neither_zero, 2] =  t[neither_zero, 1]

        axis[use_fallback] = fb

    return quat_from_axis_angle(axis, angle, out=out)


def quat_from_axis_angle(axis, angle, out=None, dtype=None) -> np.ndarray:
    """Quaternion from axis-angle pair.

    Create a quaternion representing the rotation of an given angle
    about a given unit vector

    Parameters
    ----------
    axis : ndarray, [3]
        Unit vector
    angle : number
        The angle (in radians) to rotate about axis
    out : ndarray, optional
        A location into which the result is stored. If provided, it
        must have a shape that the inputs broadcast to. If not provided or
        None, a freshly-allocated array is returned. A tuple must have
        length equal to the number of outputs.
    dtype : data-type, optional
        Overrides the data type of the result.

    Returns
    -------
    ndarray, [4]
        Quaternion.
    """

    axis = np.asarray(axis, dtype=float)
    angle = np.asarray(angle, dtype=float)

    if out is None:
        out_shape = np.broadcast_shapes(axis.shape[:-1], angle.shape)
        out = np.empty((*out_shape, 4), dtype=dtype)

    # result should be independent of the length of the given axis
    lengths_shape = (*axis.shape[:-1], 1)
    axis = axis / np.linalg.norm(axis, axis=-1).reshape(lengths_shape)

    out[..., :3] = axis * np.sin(angle / 2).reshape(lengths_shape)
    out[..., 3] = np.cos(angle / 2)

    return out


def mat_compose(translation, rotation, scaling, /, *, out=None, dtype=None) -> np.ndarray:
    """
    Compose transformation matrices given translation vectors, quaternions,
    and scaling vectors.

    Parameters
    ----------
    translation : ndarray, [3] or [num_vectors, 3]
    rotation : ndarray, [4] or [num_vectors, 4]
    scaling : ndarray, [3] or [num_vectors, 3]

    Returns
    -------
    ndarray, [num_vectors, 4, 4]
    """
    rotation    = np.asarray(rotation, dtype=float)
    translation = np.asarray(translation, dtype=float)
    scaling     = np.asarray(scaling, dtype=float)

    if rotation.ndim == 1:
        rotation = rotation[None, :]
    if translation.ndim == 1:
        translation = translation[None, :]
    if scaling.ndim == 0:
        scaling = np.full((1, 3), scaling)
    elif scaling.ndim == 1 and scaling.shape[0] == 3:
        scaling = scaling[None, :]
    elif scaling.ndim == 1:
        scaling = scaling[:, None] * np.ones(3)

    num_vectors = max(rotation.shape[0], translation.shape[0], scaling.shape[0])

    if out is None:
        out = np.zeros((num_vectors, 4, 4), dtype=dtype)
    else:
        out[..., :, :] = 0

    x, y, z, w = rotation[:, 0], rotation[:, 1], rotation[:, 2], rotation[:, 3]

    x2, y2, z2 = x + x, y + y, z + z
    xx, xy, xz = x * x2, x * y2, x * z2
    yy, yz, zz = y * y2, y * z2, z * z2
    wx, wy, wz = w * x2, w * y2, w * z2

    sx, sy, sz = scaling[:, 0], scaling[:, 1], scaling[:, 2]


    out[:, 0, 0] = (1 - (yy + zz)) * sx
    out[:, 1, 0] = (xy + wz) * sx
    out[:, 2, 0] = (xz - wy) * sx

    out[:, 0, 1] = (xy - wz) * sy
    out[:, 1, 1] = (1 - (xx + zz)) * sy
    out[:, 2, 1] = (yz + wx) * sy

    out[:, 0, 2] = (xz + wy) * sz
    out[:, 1, 2] = (yz - wx) * sz
    out[:, 2, 2] = (1 - (xx + yy)) * sz

    out[:, 0:3, 3] = translation
    out[:, 3, 3] = 1

    return out