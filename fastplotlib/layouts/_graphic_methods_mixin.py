# This is an auto-generated file and should not be modified directly

from typing import *

import numpy
import weakref

from ..graphics import *
from ..graphics._base import Graphic


class GraphicMethodsMixin:
    def __init__(self):
        pass

    def _create_graphic(self, graphic_class, *args, **kwargs) -> Graphic:
        if "center" in kwargs.keys():
            center = kwargs.pop("center")
        else:
            center = False

        if "name" in kwargs.keys():
            self._check_graphic_name_exists(kwargs["name"])

        graphic = graphic_class(*args, **kwargs)
        self.add_graphic(graphic, center=center)

        # only return a proxy to the real graphic
        return weakref.proxy(graphic)

    def add_heatmap(
        self,
        data: Any,
        vmin: int = None,
        vmax: int = None,
        cmap: str = "plasma",
        filter: str = "nearest",
        chunk_size: int = 8192,
        isolated_buffer: bool = True,
        *args,
        **kwargs
    ) -> HeatmapGraphic:
        """

        Create an Image Graphic

        Parameters
        ----------
        data: array-like
            array-like, usually numpy.ndarray, must support ``memoryview()``
            Tensorflow Tensors also work **probably**, but not thoroughly tested
            | shape must be ``[x_dim, y_dim]``

        vmin: int, optional
            minimum value for color scaling, calculated from data if not provided

        vmax: int, optional
            maximum value for color scaling, calculated from data if not provided

        cmap: str, optional, default "plasma"
            colormap to use to display the data

        filter: str, optional, default "nearest"
            interpolation filter, one of "nearest" or "linear"

        chunk_size: int, default 8192, max 8192
            chunk size for each tile used to make up the heatmap texture

        isolated_buffer: bool, default True
            If True, initialize a buffer with the same shape as the input data and then
            set the data, useful if the data arrays are ready-only such as memmaps.
            If False, the input array is itself used as the buffer.

        args:
            additional arguments passed to Graphic

        kwargs:
            additional keyword arguments passed to Graphic

        Features
        --------

        **data**: :class:`.HeatmapDataFeature`
            Manages the data buffer displayed in the HeatmapGraphic

        **cmap**: :class:`.HeatmapCmapFeature`
            Manages the colormap

        **present**: :class:`.PresentFeature`
            Control the presence of the Graphic in the scene


        """
        return self._create_graphic(
            HeatmapGraphic,
            data,
            vmin,
            vmax,
            cmap,
            filter,
            chunk_size,
            isolated_buffer,
            *args,
            **kwargs
        )

    def add_image(
        self,
        data: Any,
        vmin: int = None,
        vmax: int = None,
        cmap: str = "plasma",
        filter: str = "nearest",
        isolated_buffer: bool = True,
        *args,
        **kwargs
    ) -> ImageGraphic:
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

        cmap: str, optional, default "plasma"
            colormap to use to display the image data, ignored if data is RGB

        filter: str, optional, default "nearest"
            interpolation filter, one of "nearest" or "linear"

        isolated_buffer: bool, default True
            If True, initialize a buffer with the same shape as the input data and then
            set the data, useful if the data arrays are ready-only such as memmaps.
            If False, the input array is itself used as the buffer.

        args:
            additional arguments passed to Graphic

        kwargs:
            additional keyword arguments passed to Graphic

        Features
        --------

        **data**: :class:`.ImageDataFeature`
            Manages the data buffer displayed in the ImageGraphic

        **cmap**: :class:`.ImageCmapFeature`
            Manages the colormap

        **present**: :class:`.PresentFeature`
            Control the presence of the Graphic in the scene


        """
        return self._create_graphic(
            ImageGraphic,
            data,
            vmin,
            vmax,
            cmap,
            filter,
            isolated_buffer,
            *args,
            **kwargs
        )

    def add_line_collection(
        self,
        data: List[numpy.ndarray],
        z_position: Union[Iterable[float], float] = None,
        thickness: Union[float, Iterable[float]] = 2.0,
        colors: Union[str, Iterable[str], numpy.ndarray, Iterable[numpy.ndarray]] = "w",
        alpha: float = 1.0,
        cmap: Union[Iterable[str], str] = None,
        cmap_values: Union[numpy.ndarray, List] = None,
        name: str = None,
        metadata: Union[Iterable[Any], numpy.ndarray] = None,
        *args,
        **kwargs
    ) -> LineCollection:
        """

        Create a collection of :class:`.LineGraphic`

        Parameters
        ----------
        data: list of array-like or array
            List of line data to plot, each element must be a 1D, 2D, or 3D numpy array
            if elements are 2D, interpreted as [y_vals, n_lines]

        z_position: Iterable of float or float, optional
            | if ``float``, single position will be used for all lines
            | if ``list`` of ``float``, each value will apply to the individual lines

        thickness: float or Iterable of float, default 2.0
            | if ``float``, single thickness will be used for all lines
            | if ``list`` of ``float``, each value will apply to the individual lines

        colors: str, RGBA array, Iterable of RGBA array, or Iterable of str, default "w"
            | if single ``str`` such as "w", "r", "b", etc, represents a single color for all lines
            | if single ``RGBA array`` (tuple or list of size 4), represents a single color for all lines
            | if ``list`` of ``str``, represents color for each individual line, example ["w", "b", "r",...]
            | if ``RGBA array`` of shape [data_size, 4], represents a single RGBA array for each line

        alpha: float, optional
            alpha value for colors, if colors is a ``str``

        cmap: Iterable of str or str, optional
            | if ``str``, single cmap will be used for all lines
            | if ``list`` of ``str``, each cmap will apply to the individual lines

            .. note::
                ``cmap`` overrides any arguments passed to ``colors``

        cmap_values: 1D array-like or Iterable of numerical values, optional
            if provided, these values are used to map the colors from the cmap

        name: str, optional
            name of the line collection

        metadata: Iterable or array
            metadata associated with this collection, this is for the user to manage.
            ``len(metadata)`` must be same as ``len(data)``

        args
            passed to GraphicCollection

        kwargs
            passed to GraphicCollection

        Features
        --------

        Collections support the same features as the underlying graphic. You just have to slice the selection.

        See :class:`LineGraphic` details on the features.


        """
        return self._create_graphic(
            LineCollection,
            data,
            z_position,
            thickness,
            colors,
            alpha,
            cmap,
            cmap_values,
            name,
            metadata,
            *args,
            **kwargs
        )

    def add_line(
        self,
        data: Any,
        thickness: float = 2.0,
        colors: Union[str, numpy.ndarray, Iterable] = "w",
        alpha: float = 1.0,
        cmap: str = None,
        cmap_values: Union[numpy.ndarray, Iterable] = None,
        z_position: float = None,
        collection_index: int = None,
        *args,
        **kwargs
    ) -> LineGraphic:
        """

        Create a line Graphic, 2d or 3d

        Parameters
        ----------
        data: array-like
            Line data to plot, 2D must be of shape [n_points, 2], 3D must be of shape [n_points, 3]

        thickness: float, optional, default 2.0
            thickness of the line

        colors: str, array, or iterable, default "w"
            specify colors as a single human-readable string, a single RGBA array,
            or an iterable of strings or RGBA arrays

        cmap: str, optional
            apply a colormap to the line instead of assigning colors manually, this
            overrides any argument passed to "colors"

        cmap_values: 1D array-like or Iterable of numerical values, optional
            if provided, these values are used to map the colors from the cmap

        alpha: float, optional, default 1.0
            alpha value for the colors

        z_position: float, optional
            z-axis position for placing the graphic

        args
            passed to Graphic

        kwargs
            passed to Graphic

        Features
        --------

        **data**: :class:`.ImageDataFeature`
            Manages the line [x, y, z] positions data buffer, allows regular and fancy indexing.

        **colors**: :class:`.ColorFeature`
            Manages the color buffer, allows regular and fancy indexing.

        **cmap**: :class:`.CmapFeature`
            Manages the cmap, wraps :class:`.ColorFeature` to add additional functionality relevant to cmaps.

        **thickness**: :class:`.ThicknessFeature`
            Manages the thickness feature of the lines.

        **present**: :class:`.PresentFeature`
            Control the presence of the Graphic in the scene, set to ``True`` or ``False``


        """
        return self._create_graphic(
            LineGraphic,
            data,
            thickness,
            colors,
            alpha,
            cmap,
            cmap_values,
            z_position,
            collection_index,
            *args,
            **kwargs
        )

    def add_line_stack(
        self,
        data: List[numpy.ndarray],
        z_position: Union[Iterable[float], float] = None,
        thickness: Union[float, Iterable[float]] = 2.0,
        colors: Union[str, Iterable[str], numpy.ndarray, Iterable[numpy.ndarray]] = "w",
        alpha: float = 1.0,
        cmap: Union[Iterable[str], str] = None,
        cmap_values: Union[numpy.ndarray, List] = None,
        name: str = None,
        metadata: Union[Iterable[Any], numpy.ndarray] = None,
        separation: float = 10.0,
        separation_axis: str = "y",
        *args,
        **kwargs
    ) -> LineStack:
        """

        Create a stack of :class:`.LineGraphic` that are separated along the "x" or "y" axis.

        Parameters
        ----------
        data: list of array-like or array
            List of line data to plot, each element must be a 1D, 2D, or 3D numpy array
            if elements are 2D, interpreted as [y_vals, n_lines]

        z_position: Iterable of float or float, optional
            | if ``float``, single position will be used for all lines
            | if ``list`` of ``float``, each value will apply to the individual lines

        thickness: float or Iterable of float, default 2.0
            | if ``float``, single thickness will be used for all lines
            | if ``list`` of ``float``, each value will apply to the individual lines

        colors: str, RGBA array, Iterable of RGBA array, or Iterable of str, default "w"
            | if single ``str`` such as "w", "r", "b", etc, represents a single color for all lines
            | if single ``RGBA array`` (tuple or list of size 4), represents a single color for all lines
            | if ``list`` of ``str``, represents color for each individual line, example ["w", "b", "r",...]
            | if ``RGBA array`` of shape [data_size, 4], represents a single RGBA array for each line

        cmap: Iterable of str or str, optional
            | if ``str``, single cmap will be used for all lines
            | if ``list`` of ``str``, each cmap will apply to the individual lines

            .. note::
                ``cmap`` overrides any arguments passed to ``colors``

        cmap_values: 1D array-like or Iterable of numerical values, optional
            if provided, these values are used to map the colors from the cmap

        metadata: Iterable or array
            metadata associated with this collection, this is for the user to manage.
            ``len(metadata)`` must be same as ``len(data)``

        separation: float, default 10
            space in between each line graphic in the stack

        separation_axis: str, default "y"
            axis in which the line graphics in the stack should be separated

        name: str, optional
            name of the line stack

        kwargs
            passed to LineCollection

        Features
        --------

        Collections support the same features as the underlying graphic. You just have to slice the selection.

        See :class:`LineGraphic` details on the features.


        """
        return self._create_graphic(
            LineStack,
            data,
            z_position,
            thickness,
            colors,
            alpha,
            cmap,
            cmap_values,
            name,
            metadata,
            separation,
            separation_axis,
            *args,
            **kwargs
        )

    def add_scatter(
        self,
        data: numpy.ndarray,
        sizes: Union[float, numpy.ndarray, Iterable[float]] = 1,
        colors: Union[str, numpy.ndarray, Iterable[str]] = "w",
        alpha: float = 1.0,
        cmap: str = None,
        cmap_values: Union[numpy.ndarray, List] = None,
        z_position: float = 0.0,
        *args,
        **kwargs
    ) -> ScatterGraphic:
        """

        Create a Scatter Graphic, 2d or 3d

        Parameters
        ----------
        data: array-like
            Scatter data to plot, 2D must be of shape [n_points, 2], 3D must be of shape [n_points, 3]

        sizes: float or iterable of float, optional, default 1.0
            size of the scatter points

        colors: str, array, or iterable, default "w"
            specify colors as a single human readable string, a single RGBA array,
            or an iterable of strings or RGBA arrays

        cmap: str, optional
            apply a colormap to the scatter instead of assigning colors manually, this
            overrides any argument passed to "colors"

        cmap_values: 1D array-like or list of numerical values, optional
            if provided, these values are used to map the colors from the cmap

        alpha: float, optional, default 1.0
            alpha value for the colors

        z_position: float, optional
            z-axis position for placing the graphic

        args
            passed to Graphic

        kwargs
            passed to Graphic

        Features
        --------

        **data**: :class:`.ImageDataFeature`
            Manages the line [x, y, z] positions data buffer, allows regular and fancy indexing.

        **colors**: :class:`.ColorFeature`
            Manages the color buffer, allows regular and fancy indexing.

        **cmap**: :class:`.CmapFeature`
            Manages the cmap, wraps :class:`.ColorFeature` to add additional functionality relevant to cmaps.

        **present**: :class:`.PresentFeature`
            Control the presence of the Graphic in the scene, set to ``True`` or ``False``


        """
        return self._create_graphic(
            ScatterGraphic,
            data,
            sizes,
            colors,
            alpha,
            cmap,
            cmap_values,
            z_position,
            *args,
            **kwargs
        )

    def add_text(
        self,
        text: str,
        position: Tuple[int] = (0, 0, 0),
        size: int = 14,
        face_color: Union[str, numpy.ndarray] = "w",
        outline_color: Union[str, numpy.ndarray] = "w",
        outline_thickness=0,
        screen_space: bool = True,
        anchor: str = "middle-center",
        *args,
        **kwargs
    ) -> TextGraphic:
        """

        Create a text Graphic

        Parameters
        ----------
        text: str
            display text

        position: int tuple, default (0, 0, 0)
            int tuple indicating location of text in scene

        size: int, default 10
            text size

        face_color: str or array, default "w"
            str or RGBA array to set the color of the text

        outline_color: str or array, default "w"
            str or RGBA array to set the outline color of the text

        outline_thickness: int, default 0
            text outline thickness

        screen_space: bool = True
            whether the text is rendered in screen space, in contrast to world space

        name: str, optional
            name of graphic, passed to Graphic

        anchor: str, default "middle-center"
            position of the origin of the text
            a string representing the vertical and horizontal anchors, separated by a dash

            * Vertical values: "top", "middle", "baseline", "bottom"
            * Horizontal values: "left", "center", "right"

        """
        return self._create_graphic(
            TextGraphic,
            text,
            position,
            size,
            face_color,
            outline_color,
            outline_thickness,
            screen_space,
            anchor,
            *args,
            **kwargs
        )
