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

    def add_image(
        self,
        data: Any,
        vmin: int = None,
        vmax: int = None,
        cmap: str = "plasma",
        interpolation: str = "nearest",
        cmap_interpolation: str = "linear",
        isolated_buffer: bool = True,
        **kwargs
    ) -> ImageGraphic:
        """

        Create an Image Graphic

        Parameters
        ----------
        data: array-like
            array-like, usually numpy.ndarray, must support ``memoryview()``
            | shape must be ``[x_dim, y_dim]``

        vmin: int, optional
            minimum value for color scaling, calculated from data if not provided

        vmax: int, optional
            maximum value for color scaling, calculated from data if not provided

        cmap: str, optional, default "plasma"
            colormap to use to display the data

        interpolation: str, optional, default "nearest"
            interpolation filter, one of "nearest" or "linear"

        cmap_interpolation: str, optional, default "linear"
            colormap interpolation method, one of "nearest" or "linear"

        isolated_buffer: bool, default True
            If True, initialize a buffer with the same shape as the input data and then
            set the data, useful if the data arrays are ready-only such as memmaps.
            If False, the input array is itself used as the buffer.

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
            ImageGraphic,
            data,
            vmin,
            vmax,
            cmap,
            interpolation,
            cmap_interpolation,
            isolated_buffer,
            **kwargs
        )

    def add_line_collection(
        self,
        data: List[numpy.ndarray],
        thickness: Union[float, Sequence[float]] = 2.0,
        colors: Union[str, Sequence[str], numpy.ndarray, Sequence[numpy.ndarray]] = "w",
        uniform_colors: bool = False,
        alpha: float = 1.0,
        cmap: Union[Sequence[str], str] = None,
        cmap_values: Union[numpy.ndarray, List] = None,
        name: str = None,
        metadata: Union[Sequence[Any], numpy.ndarray] = None,
        isolated_buffer: bool = True,
        **kwargs
    ) -> LineCollection:
        """

        Create a collection of :class:`.LineGraphic`

        Parameters
        ----------
        data: list of array-like or array
            List of line data to plot, each element must be a 1D, 2D, or 3D numpy array
            if elements are 2D, interpreted as [y_vals, n_lines]

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

        kwargs
            passed to Graphic

        Features
        --------

        Collections support the same features as the underlying graphic. You just have to slice the selection.

        See :class:`LineGraphic` details on the features.


        """
        return self._create_graphic(
            LineCollection,
            data,
            thickness,
            colors,
            uniform_colors,
            alpha,
            cmap,
            cmap_values,
            name,
            metadata,
            isolated_buffer,
            **kwargs
        )

    def add_line(
        self,
        data: Any,
        thickness: float = 2.0,
        colors: Union[str, numpy.ndarray, Iterable] = "w",
        uniform_color: bool = False,
        alpha: float = 1.0,
        cmap: str = None,
        cmap_values: Union[numpy.ndarray, Iterable] = None,
        isolated_buffer: bool = True,
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

        **kwargs
            passed to Graphic


        """
        return self._create_graphic(
            LineGraphic,
            data,
            thickness,
            colors,
            uniform_color,
            alpha,
            cmap,
            cmap_values,
            isolated_buffer,
            **kwargs
        )

    def add_line_stack(
        self,
        data: List[numpy.ndarray],
        thickness: Union[float, Iterable[float]] = 2.0,
        colors: Union[str, Iterable[str], numpy.ndarray, Iterable[numpy.ndarray]] = "w",
        alpha: float = 1.0,
        cmap: Union[Iterable[str], str] = None,
        cmap_values: Union[numpy.ndarray, List] = None,
        name: str = None,
        metadata: Union[Iterable[Any], numpy.ndarray] = None,
        separation: float = 10.0,
        separation_axis: str = "y",
        **kwargs
    ) -> LineStack:
        """

        Create a stack of :class:`.LineGraphic` that are separated along the "x" or "y" axis.

        Parameters
        ----------
        data: list of array-like or array
            List of line data to plot, each element must be a 1D, 2D, or 3D numpy array
            if elements are 2D, interpreted as [y_vals, n_lines]

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
            thickness,
            colors,
            alpha,
            cmap,
            cmap_values,
            name,
            metadata,
            separation,
            separation_axis,
            **kwargs
        )

    def add_scatter(
        self,
        data: Any,
        colors: str | numpy.ndarray | tuple[float] | list[float] | list[str] = "w",
        uniform_color: bool = False,
        alpha: float = 1.0,
        cmap: str = None,
        cmap_values: numpy.ndarray = None,
        isolated_buffer: bool = True,
        sizes: Union[float, numpy.ndarray, Iterable[float]] = 1,
        uniform_size: bool = False,
        **kwargs
    ) -> ScatterGraphic:
        """

        Create a Scatter Graphic, 2d or 3d

        Parameters
        ----------
        data: array-like
            Scatter data to plot, 2D must be of shape [n_points, 2], 3D must be of shape [n_points, 3]

        colors: str, array, or iterable, default "w"
            specify colors as a single human readable string, a single RGBA array,
            or an iterable of strings or RGBA arrays

        uniform_color: bool, default False
            if True, uses a uniform buffer for the scatter point colors,
            basically saves GPU VRAM when the entire line has a single color

        alpha: float, optional, default 1.0
            alpha value for the colors

        cmap: str, optional
            apply a colormap to the scatter instead of assigning colors manually, this
            overrides any argument passed to "colors"

        cmap_values: 1D array-like or list of numerical values, optional
            if provided, these values are used to map the colors from the cmap

        isolated_buffer: bool, default True
            whether the buffers should be isolated from the user input array.
            Generally always ``True``, ``False`` is for rare advanced use.

        sizes: float or iterable of float, optional, default 1.0
            size of the scatter points

        uniform_size: bool, default False
            if True, uses a uniform buffer for the scatter point sizes,
            basically saves GPU VRAM when all scatter points are the same size

        kwargs
            passed to Graphic


        """
        return self._create_graphic(
            ScatterGraphic,
            data,
            colors,
            uniform_color,
            alpha,
            cmap,
            cmap_values,
            isolated_buffer,
            sizes,
            uniform_size,
            **kwargs
        )

    def add_text(
        self,
        text: str,
        font_size: float | int = 14,
        face_color: str | numpy.ndarray | list[float] | tuple[float] = "w",
        outline_color: str | numpy.ndarray | list[float] | tuple[float] = "w",
        outline_thickness: float | int = 0,
        screen_space: bool = True,
        offset: tuple[float] = (0, 0, 0),
        anchor: str = "middle-center",
        **kwargs
    ) -> TextGraphic:
        """

        Create a text Graphic

        Parameters
        ----------
        text: str
            text to display

        font_size: float | int, default 10
            font size

        face_color: str or array, default "w"
            str or RGBA array to set the color of the text

        outline_color: str or array, default "w"
            str or RGBA array to set the outline color of the text

        outline_thickness: float | int, default 0
            text outline thickness

        screen_space: bool = True
            if True, text size is in screen space, if False the text size is in data space

        offset: (float, float, float), default (0, 0, 0)
            places the text at this location

        anchor: str, default "middle-center"
            position of the origin of the text
            a string representing the vertical and horizontal anchors, separated by a dash

            * Vertical values: "top", "middle", "baseline", "bottom"
            * Horizontal values: "left", "center", "right"

        **kwargs
            passed to Graphic


        """
        return self._create_graphic(
            TextGraphic,
            text,
            font_size,
            face_color,
            outline_color,
            outline_thickness,
            screen_space,
            offset,
            anchor,
            **kwargs
        )
