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
        """
        ``NDPositionsProcessor`` subclass that reads positional data from the columns of a ``pandas.DataFrame``
        instead of an n-dimensional array.

        Each entry in ``columns`` names the columns that hold the coordinates of one graphic, so the number of
        entries is the number of graphics in the collection and the number of rows is the size of the ``p`` dim.
        There are no additional slider dims, ``p`` is the only one.

        Available as ``ndp_extras.NDPP_Pandas`` when ``pandas`` is installed, pass it as the ``processor`` to
        ``NDWSubplot.add_nd_lines()``, ``add_nd_scatter()`` or ``add_nd_timeseries()``.

        Parameters
        ----------
        data: pd.DataFrame
            DataFrame holding the coordinates, one column per coordinate of each graphic.

        spatial_dims: tuple[str, str, str]
            The 3 spatial dims **in display order**: ``(n_graphics, p, <value dim>)``. These are also used as
            the ``dims``, since a DataFrame has no other dims to name.

        columns: list[tuple[str, str] | tuple[str, str, str]]
            One entry per graphic, each a tuple of 2 or 3 column names giving the (x, y) or (x, y, z)
            coordinates of that graphic. Ex: ``[("nose_x", "nose_y"), ("tail_x", "tail_y")]`` for two keypoint
            trajectories.

        tooltip_columns: list[str], optional
            One column name per graphic. The value of that column at the hovered datapoint is shown in the
            tooltip, ex: a per-keypoint likelihood column. Must be the same length as ``columns``.

        kwargs
            passed to :class:`.NDPositionsProcessor`, i.e. ``display_window``, ``max_display_datapoints``,
            ``slider_dim_transforms``, ``datapoints_window_func`` and ``spatial_func``.

        """
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
        """get or set the managed DataFrame, the new DataFrame must have the same ``columns``"""
        return self._data

    @data.setter
    def data(self, data: pd.DataFrame):
        if not isinstance(data, pd.DataFrame):
            raise TypeError

        self._data = data

    @property
    def columns(self) -> list[tuple[str, str] | tuple[str, str, str]]:
        """the columns that hold the coordinates of each graphic, one entry per graphic"""
        return self._columns

    @property
    def dims(self) -> tuple[str, str, str]:
        """dim names, the same as :attr:`spatial_dims` since a DataFrame has no other dims"""
        return self._dims

    @property
    def shape(self) -> dict[str, int]:
        """interpreted shape of the data, the number of graphics, the number of rows, and the value dim"""
        # n_graphical_elements, n_timepoints, 2
        return {self.dims[0]: len(self.columns), self.dims[1]: self.data.index.size, self.dims[2]: 2}

    @property
    def ndim(self) -> int:
        """number of dims, always 3"""
        return len(self.shape)

    @property
    def tooltip(self) -> bool:
        """whether ``tooltip_columns`` were provided, i.e. whether a custom tooltip is formatted"""
        return self._tooltip

    def tooltip_format(self, n: int, p: int):
        """
        Format the tooltip for a hovered datapoint using the ``tooltip_columns``.

        Parameters
        ----------
        n: int
            index of the graphic within the collection

        p: int
            index of the datapoint within the current display window

        Returns
        -------
        str
            value of that graphic's tooltip column at this datapoint

        """
        # datapoint index w.r.t. full data
        p += self._dw_slice.start
        return str(self.data[self._tooltip_columns[n]][p])

    async def get(self, indices: dict[str, Any]) -> dict[str, np.ndarray]:
        """
        Get the data slice to display at the given indices.

        Stacks the ``columns`` of each graphic into a ``[n_graphics, p, 3]`` array for the current display
        window, then applies the ``datapoints_window_func`` and ``spatial_func``. Entries of ``columns`` that
        name only (x, y) leave the z coordinate as ``0``.

        Parameters
        ----------
        indices: dict[str, Any]
            Reference-space value for the ``p`` dim, ex: ``{"time": 46.397}``.

        Returns
        -------
        dict[str, np.ndarray]
            ``"data"`` holds the data slice, the remaining keys are the windowed graphic features.

        """
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
