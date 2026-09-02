from typing import Callable, Any, Literal

import numpy as np

from ...graphics.image import TupleYUV
from ._nd_image import NDImageProcessor
from ._async import run_in_thread_pool


class VideoProcessor(NDImageProcessor):
    async def get_window_output(self, indices: dict[str, Any]) -> TupleYUV | np.ndarray:
        """
        Applies any window functions and returns squeezed sliced array transposed in the order of the given spatial dims

        Parameters
        ----------
        indices

        Returns
        -------

        """
        # windowed slice if user set any window funcs
        windowed_slice = await self._get_raw_data_slice(indices)

        if isinstance(windowed_slice, (tuple, list)):
            return tuple(a.squeeze() for a in windowed_slice)

        # convert to numpy array
        return np.asarray(windowed_slice).squeeze()

    async def get(self, indices: dict[str, Any]) -> TupleYUV | np.ndarray:
        """
        Similar to NDImage.get() but accounts for TupleYUV output.
        """
        # this will be squeezed output, with dims in the order of the user set spatial dims
        window_output = await self.get_window_output(indices)

        if self.spatial_func is not None:
            window_output = await run_in_thread_pool(
                self._executor, self._spatial_func, window_output
            )

        if isinstance(window_output, tuple):
            return tuple(a.transpose(*self.spatial_dims_indices) for a in window_output)

        return window_output.transpose(*self.spatial_dims_indices)
