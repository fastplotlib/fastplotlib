import numpy as np
import pandas as pd

from .core import NDPositionsProcessor


class NDPP_Pandas(NDPositionsProcessor):
    def __init__(
            self,
            data: pd.DataFrame,
            columns: list[tuple[str, str] | tuple[str, str, str]],
            tooltip_columns: list[str] = None,
            max_display_datapoints: int = 1_000,
            **kwargs,
    ):
        data = data

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
            max_display_datapoints=max_display_datapoints,
            **kwargs,
        )

    @property
    def data(self) -> pd.DataFrame:
        return self._data

    def _validate_data(self, data: pd.DataFrame):
        if not isinstance(data, pd.DataFrame):
            raise TypeError

        return data

    @property
    def columns(self) -> list[tuple[str, str] | tuple[str, str, str]]:
        return self._columns

    @property
    def multi(self) -> bool:
        return True

    @multi.setter
    def multi(self, v):
        pass

    @property
    def shape(self) -> tuple[int, ...]:
        # n_graphical_elements, n_timepoints, 2
        return len(self.columns), self.data.index.size, 2

    @property
    def ndim(self) -> int:
        return len(self.shape)

    @property
    def n_slider_dims(self) -> int:
        return 1

    @property
    def tooltip(self) -> bool:
        return self._tooltip

    def tooltip_format(self, n: int, p: int):
        # datapoint index w.r.t. full data
        p += self._slices[-1].start
        return str(self.data[self._tooltip_columns[n]][p])

    def get(self, indices: tuple[float | int, ...]) -> np.ndarray:
        if not isinstance(indices, tuple):
            raise TypeError(".get() must receive a tuple of float | int indices")
        # assume no additional slider dims, only time slider dim
        self._slices = self._get_dw_slices(indices)


        gdata_shape = len(self.columns), self._slices[-1].stop - self._slices[-1].start, 3
        gdata = np.zeros(shape=gdata_shape, dtype=np.float32)

        for i, col in enumerate(self.columns):
            gdata[i, :, :len(col)] = np.column_stack(
                [self.data[c][self._slices[-1]] for c in col]
            )

        return gdata
