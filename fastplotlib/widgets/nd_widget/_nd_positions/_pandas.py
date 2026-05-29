from typing import Any

import numpy as np
import pandas as pd

from ._nd_positions import NDPositionsProcessor


class NDPP_Pandas(NDPositionsProcessor):
    def __init__(
            self,
            data: pd.DataFrame,
            spatial_dims: tuple[str, str, str],  # [l, p, d] dims in order
            columns: list[tuple[str, str] | tuple[str, str, str]],
            tooltip_columns: list[str] = None,
            **kwargs,
    ):
        self._columns = columns

        if tooltip_columns is not None:
            if len(tooltip_columns) != len(self.columns):
                raise ValueError
            self._tooltip_columns = tooltip_columns
            self._tooltip = True
        else:
            self._tooltip_columns = None
            self._tooltip = False

        super().__init__(
            data=data,
            dims=spatial_dims,
            spatial_dims=spatial_dims,
            **kwargs,
        )

        self._dw_slice = None

    @property
    def data(self) -> pd.DataFrame:
        return self._data

    @data.setter
    def data(self, data: pd.DataFrame):
        if not isinstance(data, pd.DataFrame):
            raise TypeError

        self._data = data

    @property
    def columns(self) -> list[tuple[str, str] | tuple[str, str, str]]:
        return self._columns

    @property
    def dims(self) -> tuple[str, str, str]:
        return self._dims

    @property
    def shape(self) -> dict[str, int]:
        # n_graphical_elements, n_timepoints, 2
        return {self.dims[0]: len(self.columns), self.dims[1]: self.data.index.size, self.dims[2]: 2}

    @property
    def ndim(self) -> int:
        return len(self.shape)

    @property
    def tooltip(self) -> bool:
        return self._tooltip

    def tooltip_format(self, n: int, p: int):
        # datapoint index w.r.t. full data
        p += self._dw_slice.start
        return str(self.data[self._tooltip_columns[n]][p])

    async def get(self, indices: dict[str, Any]) -> dict[str, np.ndarray]:
        # TODO: LOD by using a step size according to max_p
        # TODO: Also what to do if display_window is None and data
        #  hasn't changed when indices keeps getting set, cache?

        # assume no additional slider dims
        self._dw_slice = self._get_dw_slice(indices)

        column_stacks = [
            np.column_stack(
                [self.data[c][self._dw_slice] for c in col]
            ) for col in self.columns
        ]
        if len(column_stacks) > 0:
            n_samples = column_stacks[0].shape[0]
        else:
            n_samples = 0

        gdata_shape = len(self.columns), n_samples, 3

        graphic_data = np.zeros(shape=gdata_shape, dtype=np.float32)

        for i, (col, column_stack) in enumerate(zip(self.columns, column_stacks)):
            graphic_data[i, :, :len(col)] = column_stack

        data = self._finalize(graphic_data)
        other = self._get_other_features(data, self._dw_slice)

        return {
            "data": data,
            **other,
        }
