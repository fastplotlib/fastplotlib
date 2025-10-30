# This is an auto-generated file and should not be modified directly

from typing import *

import numpy

import pygfx

from ..graphics import *
from ..graphics._base import Graphic


class GraphicMethodsMixin:
    def _create_graphic(self, graphic_class, *args, **kwargs) -> Graphic:
        if "center" in kwargs.keys():
            center = kwargs.pop("center")
        else:
            center = False

        if "name" in kwargs.keys():
            self._check_graphic_name_exists(kwargs["name"])

        graphic = graphic_class(*args, **kwargs)
        self.add_graphic(graphic, center=center)

        return graphic

    def add_image(
        self,
        data: Any,
        vmin: float = None,
        vmax: float = None,
        cmap: str = "plasma",
        interpolation: str = "nearest",
        cmap_interpolation: str = "linear",
        isolated_buffer: bool = True,
        **kwargs,
    ) -> ImageGraphic:
        """

        Create an Image Graphic

        Parameters
        ----------
        data: array-like
            array-like, usually numpy.ndarray, must support ``memoryview()``
            | shape must be ``[n_rows, n_cols]``, ``[n_rows, n_cols, 3]`` for RGB or ``[n_rows, n_cols, 4]`` for RGBA

        vmin: float, optional
            minimum value for color scaling, estimated from data if not provided

        vmax: float, optional
            maximum value for color scaling, estimated from data if not provided

        cmap: str, optional, default "plasma"
            colormap to use to display the data. For supported colormaps see the
            ``cmap`` library catalogue: https://cmap-docs.readthedocs.io/en/stable/catalog/

        interpolation: str, optional, default "nearest"
            interpolation filter, one of "nearest" or "linear"

        cmap_interpolation: str, optional, default "linear"
            colormap interpolation method, one of "nearest" or "linear"

        isolated_buffer: bool, default True
            If True, initialize a buffer with the same shape as the input data and then
            set the data, useful if the data arrays are ready-only such as memmaps.
            If False, the input array is itself used as the buffer - useful if the
            array is large.

        kwargs:
            additional keyword arguments passed to :class:`.Graphic`


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
            **kwargs,
        )

    def add_image_volume(
        self,
        data: Any,
        mode: str = "mip",
        vmin: float = None,
        vmax: float = None,
        cmap: str = "plasma",
        interpolation: str = "linear",
        cmap_interpolation: str = "linear",
        plane: tuple[float, float, float, float] = (0, 0, -1, 0),
        threshold: float = 0.5,
        step_size: float = 1.0,
        substep_size: float = 0.1,
        emissive: str | tuple | numpy.ndarray = (0, 0, 0),
        shininess: int = 30,
        isolated_buffer: bool = True,
        **kwargs,
    ) -> ImageVolumeGraphic:
        """

        Create an ImageVolumeGraphic.

        Parameters
        ----------
        data: array-like
            array-like, usually numpy.ndarray, must support ``memoryview()``.
            Shape must be [n_planes, n_rows, n_cols] for grayscale, or [n_planes, n_rows, n_cols, 3 | 4] for RGB(A)

        mode: str, default "mip"
            render mode, one of "mip", "minip", "iso" or "slice"

        vmin: float
            lower contrast limit

        vmax: float
            upper contrast limit

        cmap: str, default "plasma"
            colormap for grayscale volumes

        interpolation: str, default "linear"
            interpolation method for sampling pixels

        cmap_interpolation: str, default "linear"
            interpolation method for sampling from colormap

        plane: (float, float, float, float), default (0, 0, -1, 0)
            Slice volume at this plane. Sets (a, b, c, d) in the equation the defines a plane: ax + by + cz + d = 0.
            Used only if `mode` = "slice"

        threshold : float, default 0.5
            The threshold texture value at which the surface is rendered.
            Used only if `mode` = "iso"

        step_size : float, default 1.0
            The size of the initial ray marching step for the initial surface finding. Smaller values will result in
            more accurate surfaces but slower rendering.
            Used only if `mode` = "iso"

        substep_size : float, default 0.1
            The size of the raymarching step for the refined surface finding. Smaller values will result in more
            accurate surfaces but slower rendering.
            Used only if `mode` = "iso"

        emissive : Color, default (0, 0, 0, 1)
            The emissive color of the surface. I.e. the color that the object emits even when not lit by a light
            source. This color is added to the final color and unaffected by lighting. The alpha channel is ignored.
            Used only if `mode` = "iso"

        shininess : int, default 30
            How shiny the specular highlight is; a higher value gives a sharper highlight.
            Used only if `mode` = "iso"

        isolated_buffer: bool, default True
            If True, initialize a buffer with the same shape as the input data and then set the data, useful if the
            data arrays are ready-only such as memmaps. If False, the input array is itself used as the
            buffer - useful if the array is large.

        kwargs
            additional keyword arguments passed to :class:`.Graphic`


        """
        return self._create_graphic(
            ImageVolumeGraphic,
            data,
            mode,
            vmin,
            vmax,
            cmap,
            interpolation,
            cmap_interpolation,
            plane,
            threshold,
            step_size,
            substep_size,
            emissive,
            shininess,
            isolated_buffer,
            **kwargs,
        )

    def add_line_collection(
        self,
        data: Union[numpy.ndarray, List[numpy.ndarray]],
        thickness: Union[float, Sequence[float]] = 2.0,
        colors: Union[str, Sequence[str], numpy.ndarray, Sequence[numpy.ndarray]] = "w",
        uniform_colors: bool = False,
        cmap: Union[Sequence[str], str] = None,
        cmap_transform: Union[numpy.ndarray, List] = None,
        name: str = None,
        names: list[str] = None,
        metadata: Any = None,
        metadatas: Union[Sequence[Any], numpy.ndarray] = None,
        isolated_buffer: bool = True,
        kwargs_lines: list[dict] = None,
        **kwargs,
    ) -> LineCollection:
        """

        Create a collection of :class:`.LineGraphic`

        Parameters
        ----------
        data: list of array-like
            List or array-like of multiple line data to plot

            | if ``list`` each item in the list must be a 1D, 2D, or 3D numpy array
            | if  array-like, must be of shape [n_lines, n_points_line, y | xy | xyz]

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

        cmap_transform: 1D array-like of numerical values, optional
            if provided, these values are used to map the colors from the cmap

        name: str, optional
            name of the line collection as a whole

        names: list[str], optional
            names of the individual lines in the collection, ``len(names)`` must equal ``len(data)``

        metadata: Any
            meatadata associated with the collection as a whole

        metadatas: Iterable or array
            metadata for each individual line associated with this collection, this is for the user to manage.
            ``len(metadata)`` must be same as ``len(data)``

        kwargs_lines: list[dict], optional
            list of kwargs passed to the individual lines, ``len(kwargs_lines)`` must equal ``len(data)``

        kwargs_collection
            kwargs for the collection, passed to GraphicCollection


        """
        return self._create_graphic(
            LineCollection,
            data,
            thickness,
            colors,
            uniform_colors,
            cmap,
            cmap_transform,
            name,
            names,
            metadata,
            metadatas,
            isolated_buffer,
            kwargs_lines,
            **kwargs,
        )

    def add_line(
        self,
        data: Any,
        thickness: float = 2.0,
        colors: Union[str, numpy.ndarray, Sequence] = "w",
        uniform_color: bool = False,
        cmap: str = None,
        cmap_transform: Union[numpy.ndarray, Sequence] = None,
        isolated_buffer: bool = True,
        size_space: str = "screen",
        **kwargs,
    ) -> LineGraphic:
        """

        Create a line Graphic, 2d or 3d

        Parameters
        ----------
        data: array-like
            Line data to plot. Can provide 1D, 2D, or a 3D data.
            | If passing a 1D array, it is used to set the y-values and the x-values are generated as an integer range
            from [0, data.size]
            | 2D data must be of shape [n_points, 2]. 3D data must be of shape [n_points, 3]

        thickness: float, optional, default 2.0
            thickness of the line

        colors: str, array, or iterable, default "w"
            specify colors as a single human-readable string, a single RGBA array,
            or a Sequence (array, tuple, or list) of strings or RGBA arrays

        uniform_color: bool, default ``False``
            if True, uses a uniform buffer for the line color,
            basically saves GPU VRAM when the entire line has a single color

        cmap: str, optional
            Apply a colormap to the line instead of assigning colors manually, this
            overrides any argument passed to "colors". For supported colormaps see the
            ``cmap`` library catalogue: https://cmap-docs.readthedocs.io/en/stable/catalog/

        cmap_transform: 1D array-like of numerical values, optional
            if provided, these values are used to map the colors from the cmap

        size_space: str, default "screen"
            coordinate space in which the thickness is expressed ("screen", "world", "model")

        **kwargs
            passed to :class:`.Graphic`


        """
        return self._create_graphic(
            LineGraphic,
            data,
            thickness,
            colors,
            uniform_color,
            cmap,
            cmap_transform,
            isolated_buffer,
            size_space,
            **kwargs,
        )

    def add_line_stack(
        self,
        data: List[numpy.ndarray],
        thickness: Union[float, Iterable[float]] = 2.0,
        colors: Union[str, Iterable[str], numpy.ndarray, Iterable[numpy.ndarray]] = "w",
        cmap: Union[Iterable[str], str] = None,
        cmap_transform: Union[numpy.ndarray, List] = None,
        name: str = None,
        names: list[str] = None,
        metadata: Any = None,
        metadatas: Union[Sequence[Any], numpy.ndarray] = None,
        isolated_buffer: bool = True,
        separation: float = 10.0,
        separation_axis: str = "y",
        kwargs_lines: list[dict] = None,
        **kwargs,
    ) -> LineStack:
        """

        Create a stack of :class:`.LineGraphic` that are separated along the "x" or "y" axis.

        Parameters
        ----------
        data: list of array-like
            List or array-like of multiple line data to plot

            | if ``list`` each item in the list must be a 1D, 2D, or 3D numpy array
            | if  array-like, must be of shape [n_lines, n_points_line, y | xy | xyz]

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

        cmap_transform: 1D array-like of numerical values, optional
            if provided, these values are used to map the colors from the cmap

        name: str, optional
            name of the line collection as a whole

        names: list[str], optional
            names of the individual lines in the collection, ``len(names)`` must equal ``len(data)``

        metadata: Any
            metadata associated with the collection as a whole

        metadatas: Iterable or array
            metadata for each individual line associated with this collection, this is for the user to manage.
            ``len(metadata)`` must be same as ``len(data)``

        separation: float, default 10
            space in between each line graphic in the stack

        separation_axis: str, default "y"
            axis in which the line graphics in the stack should be separated


        kwargs_lines: list[dict], optional
            list of kwargs passed to the individual lines, ``len(kwargs_lines)`` must equal ``len(data)``

        kwargs_collection
            kwargs for the collection, passed to GraphicCollection


        """
        return self._create_graphic(
            LineStack,
            data,
            thickness,
            colors,
            cmap,
            cmap_transform,
            name,
            names,
            metadata,
            metadatas,
            isolated_buffer,
            separation,
            separation_axis,
            kwargs_lines,
            **kwargs,
        )

    def add_scatter(
        self,
        data: Any,
        colors: Union[str, numpy.ndarray, Sequence[float], Sequence[str]] = "w",
        uniform_color: bool = False,
        cmap: str = None,
        cmap_transform: numpy.ndarray = None,
        mode: Literal["markers", "simple", "gaussian", "image"] = "markers",
        markers: Union[str, numpy.ndarray, Sequence[str]] = "o",
        uniform_marker: bool = False,
        custom_sdf: str = None,
        edge_colors: Union[
            str, pygfx.utils.color.Color, numpy.ndarray, Sequence[float]
        ] = "black",
        uniform_edge_color: bool = True,
        edge_width: float = 1.0,
        image: numpy.ndarray = None,
        point_rotations: float | numpy.ndarray = 0,
        point_rotation_mode: Literal["uniform", "vertex", "curve"] = "uniform",
        sizes: Union[float, numpy.ndarray, Sequence[float]] = 1,
        uniform_size: bool = False,
        size_space: str = "screen",
        isolated_buffer: bool = True,
        **kwargs,
    ) -> ScatterGraphic:
        """

        Create a Scatter Graphic, 2d or 3d

        Parameters
        ----------
        data: array-like
            Scatter data to plot, Can provide 2D, or a 3D data. 2D data must be of shape [n_points, 2].
            3D data must be of shape [n_points, 3]

        colors: str, array, tuple, list, Sequence, default "w"
            specify colors as a single human-readable string, a single RGBA array,
            or a Sequence (array, tuple, or list) of strings or RGBA arrays

        uniform_color: bool, default False
            if True, uses a uniform buffer for the scatter point colors. Useful if you need to
            save GPU VRAM when all points have the same color.

        cmap: str, optional
            apply a colormap to the scatter instead of assigning colors manually, this
            overrides any argument passed to "colors".  For supported colormaps see the
            ``cmap`` library catalogue: https://cmap-docs.readthedocs.io/en/stable/catalog/

        cmap_transform: 1D array-like or list of numerical values, optional
            if provided, these values are used to map the colors from the cmap

        mode: one of: "markers", "simple", "gaussian", "image", default "markers"
            The scatter points mode, cannot be changed after the graphic has been created.

            * markers: represent points with various or custom markers, default
            * simple: all scatters points are simple circles
            * gaussian: each point is a gaussian blob
            * image: use an image for each point, pass an array to the `image` kwarg, these are also called sprites

        markers: None | str | np.ndarray | Sequence[str], default "o"
            The shape of the markers when `mode` is "markers"

            Supported values:

            * A string from pygfx.MarkerShape enum
            * Matplotlib compatible characters: "osD+x^v<>*".
            * Unicode symbols: "●○■♦♥♠♣✳▲▼◀▶".
            * Emojis: "❤️♠️♣️♦️💎💍✳️📍".
            * A string containing the value "custom". In this case, the WGSL
            code defined by ``custom_sdf`` will be used.

        uniform_marker: bool, default False
            Use the same marker for all points. Only valid when `mode` is "markers". Useful if you need to use
            the same marker for all points and want to save GPU RAM.

        custom_sdf: str = None,
            The SDF code for the marker shape when the marker is set to custom.
            Can be used when `mode` is "markers".

            Negative values are inside the shape, positive values are outside the
            shape.

            The SDF's takes in two parameters `coords: vec2<f32>` and `size: f32`.
            The first is a WGSL coordinate and `size` is the overall size of
            the texture. The returned value should be the signed distance from
            any edge of the shape. Distances (positive and negative) that are
            less than half the `edge_width` in absolute terms will be colored
            with the `edge_color`. Other negative distances will be colored by
            `colors`.

        edge_colors: str | np.ndarray | pygfx.Color | Sequence[float], default "black"
            edge color of the markers, used when `mode` is "markers"

        uniform_edge_color: bool, default True
            Set the same edge color for all markers. Useful for saving GPU RAM.

        edge_width: float = 1.0,
            Width of the marker edges. used when `mode` is "markers".

        image: ArrayLike, optional
            renders an image at the scatter points, also known as sprites.
            The image color is multiplied with the point's "normal" color.

        point_rotations: float | ArrayLike = 0,
            The rotation of the scatter points in radians. Default 0. A single float rotation value can be set on all
            points, or an array of rotation values can be used to set per-point rotations

        point_rotation_mode: one of: "uniform" | "vertex" | "curve", default "uniform"
            * uniform: set the same rotation for every point, useful to save GPU RAM
            * vertex: set per-vertex rotations
            * curve: The rotation follows the curve of the line defined by the points (in screen space)

        sizes: float or iterable of float, optional, default 1.0
            sizes of the scatter points

        uniform_size: bool, default False
            if True, uses a uniform buffer for the scatter point sizes. Useful if you need to
            save GPU VRAM when all points have the same size.

        size_space: str, default "screen"
            coordinate space in which the size is expressed, one of ("screen", "world", "model")

        isolated_buffer: bool, default True
            whether the buffers should be isolated from the user input array.
            Generally always ``True``, ``False`` is for rare advanced use if you have large arrays.

        kwargs
            passed to :class:`.Graphic`


        """
        return self._create_graphic(
            ScatterGraphic,
            data,
            colors,
            uniform_color,
            cmap,
            cmap_transform,
            mode,
            markers,
            uniform_marker,
            custom_sdf,
            edge_colors,
            uniform_edge_color,
            edge_width,
            image,
            point_rotations,
            point_rotation_mode,
            sizes,
            uniform_size,
            size_space,
            isolated_buffer,
            **kwargs,
        )

    def add_text(
        self,
        text: str,
        font_size: float | int = 14,
        face_color: str | numpy.ndarray | list[float] | tuple[float] = "w",
        outline_color: str | numpy.ndarray | list[float] | tuple[float] = "w",
        outline_thickness: float = 0.0,
        screen_space: bool = True,
        offset: tuple[float] = (0, 0, 0),
        anchor: str = "middle-center",
        **kwargs,
    ) -> TextGraphic:
        """

        Create a text Graphic

        Parameters
        ----------
        text: str
            text to display

        font_size: float | int, default 10
            font size

        face_color: str, array, list, tuple, default "w"
            str or RGBA array to set the color of the text

        outline_color: str, array, list, tuple, default "w"
            str or RGBA array to set the outline color of the text

        outline_thickness: float, default 0
            relative outline thickness, value between 0.0 - 0.5

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
            passed to :class:`.Graphic`


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
            **kwargs,
        )

    def add_vector_field(
        self,
        positions: Union[numpy.ndarray, Sequence[float]],
        directions: Union[numpy.ndarray, Sequence[float]],
        color: Union[str, Sequence[float], numpy.ndarray] = "w",
        size: float = None,
        vector_shape_options: dict = None,
        **kwargs,
    ) -> VectorField:
        """

        Create a Vector Field. Similar to matplotlib quiver.

        Parameters
        ----------
        positions: np.ndarray | Sequence[float]
            positions of the vectors, array-like, shape must be [n, 2] or [n, 3] where n is the number of vectors.

        directions: np.ndarray | Sequence[float]
            directions of the vectors, array-like, shape must be [n, 2] or [n, 3] where n is the number of vectors.

        spacing: float
            average distance between pairs of nearest-neighbor vectors, used for scaling

        color: str | pygfx.Color | Sequence[float] | np.ndarray, default "w"
            color of the vectors

        size: float or None
            Size of a vector of magnitude 1 in world space for display purpose.
            Estimated from field density if not provided.

        vector_shape_options: dict
            dict with the following fields that directly describes the shape of the vector arrows.
            Overrides ``size`` argument.

                * cone_radius
                * cone_height
                * stalk_radius
                * stalk_height

        **kwargs
            passed to :class:`.Graphic`


        """
        return self._create_graphic(
            VectorField,
            positions,
            directions,
            color,
            size,
            vector_shape_options,
            **kwargs,
        )
