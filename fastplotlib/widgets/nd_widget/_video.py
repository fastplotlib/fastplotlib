from ._nd_image import NDImageProcessor, NDImage
from typing import Callable, Any, Literal

import numpy as np


class VideoProcessor(NDImageProcessor):
    """
    ``NDImageProcessor`` subclass for video data, used by ``NDWSubplot.add_video()``.

    Reads the frame at the current index directly. Window functions are not currently implemented for video.

    A YUV frame is a tuple of (Y, U, V) planes rather than a single array, so it is passed through as a tuple for
    an ``ImageYUVGraphic``.
    """

    async def get_window_output(self, indices: dict[str, Any]):
        """
        Get the frame at the given indices, squeezing out the slider dims.

        Parameters
        ----------
        indices: dict[str, Any]
            Reference-space value for each slider dim, ex: ``{"time": 46.397}``. Must provide a value for every
            slider dim.

        Returns
        -------
        np.ndarray | tuple[np.ndarray, ...]
            The frame, or a tuple of the (Y, U, V) planes if the underlying data returns YUV planes.

        """
        # windowed slice if user set any window funcs
        windowed_slice = await self._get_raw_data_slice(indices)

        if isinstance(windowed_slice, (tuple, list)):
            return tuple(a.squeeze() for a in windowed_slice)

        # convert to numpy array
        return np.asarray(windowed_slice).squeeze()
