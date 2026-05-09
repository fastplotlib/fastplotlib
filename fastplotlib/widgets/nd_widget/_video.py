from ._nd_image import NDImageProcessor, NDImage
from typing import Callable, Any, Literal

import numpy as np


class VideoProcessor(NDImageProcessor):
    async def get_window_output(self, indices: dict[str, Any]):
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
