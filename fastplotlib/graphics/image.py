from typing import *

import pygfx

from ._base import Graphic, Interaction, PreviouslyModifiedData
from .features import ImageCmapFeature, ImageDataFeature
from ..utils import quick_min_max


class ImageGraphic(Graphic, Interaction):
    feature_events = (
        "data",
        "cmap",
    )

    def __init__(
            self,
            data: Any,
            vmin: int = None,
            vmax: int = None,
            cmap: str = 'plasma',
            filter: str = "nearest",
            *args,
            **kwargs
    ):
        """
        Create an Image Graphic

        Parameters
        ----------
        data: array-like
            array-like, usually numpy.ndarray, must support ``memoryview()``
            Tensorflow Tensors also work **probably**, but not thoroughly tested
            | shape must be ``[x_dim, y_dim]`` or ``[x_dim, y_dim, rgb]``
        vmin: int, optional
            minimum value for color scaling, calculated from data if not provided
        vmax: int, optional
            maximum value for color scaling, calculated from data if not provided
        cmap: str, optional, default "nearest"
            colormap to use to display the image data, default is ``"plasma"``
        filter: str, optional, default "nearest"
            interpolation filter, one of "nearest" or "linear"
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

        super().__init__(*args, **kwargs)

        self.data = ImageDataFeature(self, data)

        if (vmin is None) or (vmax is None):
            vmin, vmax = quick_min_max(data)

        texture_view = pygfx.Texture(self.data(), dim=2).get_view(filter=filter)

        geometry = pygfx.Geometry(grid=texture_view)

        # if data is RGB
        if self.data().ndim == 3:
            self.cmap = None
            material = pygfx.ImageBasicMaterial(clim=(vmin, vmax))

        # if data is just 2D without color information, use colormap LUT
        else:
            self.cmap = ImageCmapFeature(self, cmap)
            material = pygfx.ImageBasicMaterial(clim=(vmin, vmax), map=self.cmap())

        self._world_object: pygfx.Image = pygfx.Image(
            geometry,
            material
        )

    @property
    def vmin(self) -> float:
        """Minimum contrast limit."""
        return self.world_object.material.clim[0]

    @vmin.setter
    def vmin(self, value: float):
        """Minimum contrast limit."""
        self.world_object.material.clim = (
            value,
            self.world_object.material.clim[1]
        )

    @property
    def vmax(self) -> float:
        """Maximum contrast limit."""
        return self.world_object.material.clim[1]

    @vmax.setter
    def vmax(self, value: float):
        """Maximum contrast limit."""
        self.world_object.material.clim = (
            self.world_object.material.clim[0],
            value
        )

    def _set_feature(self, feature: str, new_data: Any, indices: Any):
        pass

    def _reset_feature(self, feature: str):
        pass




