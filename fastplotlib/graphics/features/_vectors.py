from typing import Sequence

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
        {"dict key": "value", "type": "np.ndarray", "description": "new vector positions"},
    ]

    def __init__(
        self,
        positions: np.ndarray | Sequence[float],
        isolated_buffer: bool = True,
        property_name: str = "positions",
    ):
        """Manages vector field positions by managing the mesh instance buffer"""

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

        super().__init__()

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

        for i in range(self._positions.shape[0]):
            # only need to update the translation vector
            graphic.world_object.instance_buffer.data["matrix"][i][3, 0:3] = (
                self._positions[i]
            )

        graphic.world_object.instance_buffer.update_full()

        event = GraphicFeatureEvent(type="positions", info={"value": value})
        self._call_event_handlers(event)


class VectorDirections(GraphicFeature):
    event_info_spec = [
        {"dict key": "value", "type": "np.ndarray", "description": "new vector directions"},
    ]

    def __init__(
        self,
        directions: np.ndarray | Sequence[float],
        isolated_buffer: bool = True,
        property_name: str = "directions",
    ):
        """Manages vector field directions by interfacing with VectorBuffer manager"""
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

        super().__init__()

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

        old_directions = self._directions.copy()

        if value.shape[1] == 2:
            # assume 2d
            self._directions[:, :-1] = value

        else:
            self._directions[:] = value

        # use the range of the 3D space to help set a scaling factor
        range_3d = np.mean(np.ptp(graphic.positions[:], axis=0))
        # vector determines the size of the vector
        magnitudes = np.linalg.norm(self._directions, axis=1, ord=2) / range_3d

        for i in range(self._directions.shape[0]):
            # get quaternion to rotate existing vector direction to new direction
            rotation = la.quat_from_vecs(old_directions[i], self._directions[i])
            # get the new transform
            transform = la.mat_compose(graphic.positions[i], rotation, magnitudes[i])
            # set the buffer
            graphic.world_object.instance_buffer.data["matrix"][i] = transform.T

        graphic.world_object.instance_buffer.update_full()

        event = GraphicFeatureEvent(type="directions", info={"value": value})
        self._call_event_handlers(event)
