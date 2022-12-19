<<<<<<< HEAD
from typing import Tuple, Any, List
=======
from typing import *
>>>>>>> a9990946faa8b990ee2f5ab0f2fff93d99f18d9e

import numpy as np
import pygfx

from ._base import Graphic, Interaction
from ..utils import quick_min_max, get_cmap_texture


class ImageGraphic(Graphic, Interaction):
    def __init__(
            self,
            data: Any,
            vmin: int = None,
            vmax: int = None,
            cmap: str = 'plasma',
            *args,
            **kwargs
    ):
        """
        Create an Image Graphic

        Parameters
        ----------
        data: array-like, must be 2-dimensional
            | array-like, usually numpy.ndarray, must support ``memoryview()``
            | Tensorflow Tensors also work _I think_, but not thoroughly tested

        vmin: int, optional
            minimum value for color scaling, calculated from data if not provided

        vmax: int, optional
            maximum value for color scaling, calculated from data if not provided

        cmap: str, optional
            colormap to use to display the image data, default is ``"plasma"``
        args:
            additional arguments passed to Graphic
        kwargs:
            additional keyword arguments passed to Graphic

        Examples
        --------

        .. code-block:: python

            from fastplotlib import Plot

            # create a `Plot` instance
            plot = Plot()

            # make some random 2D image data
            data = np.random.rand(512, 512)

            # plot the image data
            plot.add_image(data=data)

            # show the plot
            plot.show()

        """
        if data.ndim != 2:
            raise ValueError("`data.ndim !=2`, you must pass only a 2D array to `data`")

        super().__init__(data, cmap=cmap, *args, **kwargs)

        if (vmin is None) or (vmax is None):
            vmin, vmax = quick_min_max(data)

        self.world_object: pygfx.Image = pygfx.Image(
            pygfx.Geometry(grid=pygfx.Texture(self.data, dim=2)),
            pygfx.ImageBasicMaterial(clim=(vmin, vmax), map=get_cmap_texture(cmap))
        )

    @property
    def indices(self) -> Any:
        pass

    @property
    def features(self) -> List[str]:
        pass

    def _set_feature(self, feature: str, new_data: Any, indices: Any):
        pass

    def _reset_feature(self):
        pass

    @property
    def clim(self) -> Tuple[float, float]:
        return self.world_object.material.clim

    @clim.setter
    def clim(self, levels: Tuple[float, float]):
        self.world_object.material.clim = levels

    def update_data(self, data: np.ndarray):
        self.world_object.geometry.grid.data[:] = data
        self.world_object.geometry.grid.update_range((0, 0, 0), self.world_object.geometry.grid.size)

    def update_cmap(self, cmap: str, alpha: float = 1.0):
        self.world_object.material.map = get_cmap_texture(name=cmap)
        self.world_object.geometry.grid.update_range((0, 0, 0), self.world_object.geometry.grid.size)
