from typing import Sequence

import numpy as np
import pygfx

from ._base import (
    GraphicFeature,
    BufferManager,
    GraphicFeatureEvent,
    block_reentrance,
)

# it doesn't make sense to modify just a portion of a vector field, I can't think of a use case.
# so we only allow setting the entire buffer, but allow getting portions of it
# class VectorBuffer(BufferManager):
#     """Manages the transform matrices for each mesh instance representing the vector"""
#     def __init__(self, ):


class VectorPositions(GraphicFeature):
    """Manages vector field positions by interfacing with VectorBuffer manager"""
    def __init__(self, graphic, positions: np.ndarray | Sequence[float], isolated_buffer: bool = True, property_name: str = "positions"):
        positions = np.asarray(positions, dtype=np.float32)
        if positions.ndim != 2:
            raise ValueError(
                f"vector field positions must be of shape [n, 2] or [n, 3]"
            )

        if positions.shape[1] == 2:
            positions = np.column_stack([positions[:, 0], positions[:, 1], np.zeros(positions.shape[0], dtype=np.float32)])

        elif positions.shape[1] == 3:
            pass

        else:
            raise ValueError(
                f"vector field positions must be of shape [n, 2] or [n, 3]"
            )

        self._positions = positions
        self._graphic = graphic

        super().__init__(property_name)

    @property
    def value(self) -> np.ndarray:
        return self._positions

    @block_reentrance
    def set_value(self, graphic, value: np.ndarray):
        if value.shape[0] != self._positions.shape[0]:
            raise ValueError(
                f"number of vector positions in passed array != number of vectors in graphic: {value.shape[0]} != {self._positions.shape[0]}"
            )

        if value.shape[1] == 2:
            # assume 2d
            self._positions[:, :-1] = value

        else:
            self._positions[:] = value

        for i in range(self._positions.shape[0]):
            # only need to update the translation vector
            graphic.world_object.instance_buffer.data["matrix"][i][3, 0:3] = self._positions[i]

        graphic.world_object.instance_buffer.update_full()


class VectorDirections(GraphicFeature):
    """Manager vector field directions by interfacing with VectorBuffer manager"""
    pass