# This is an auto-generated file and should not be modified directly

from fastplotlib.graphics._collection_base import *
from fastplotlib.graphics._collections import *
from fastplotlib.graphics._vectors import *
from fastplotlib.graphics.image import *
from fastplotlib.graphics.image_volume import *
from fastplotlib.graphics.inf_line import *
from fastplotlib.graphics.line import *
from fastplotlib.graphics.mesh import *
from fastplotlib.graphics.scatter import *
from fastplotlib.graphics.text import *
from fastplotlib.graphics import Graphic


class GraphicMethodsMixin:
    def _create_graphic(self, graphic_class, *args, **kwargs) -> Graphic:
        if "center" in kwargs.keys():
            center = kwargs.pop("center")
        else:
            center = False

        # ignore arguments left at their default of None, i.e. not passed by the caller
        kwargs = {k: v for k, v in kwargs.items() if v is not None}

        if "name" in kwargs.keys():
            self._check_graphic_name_exists(kwargs["name"])

        graphic = graphic_class(*args, **kwargs)
        self.add_graphic(graphic, center=center)

        return graphic

    def add_collection(
        self, data, name: str = None, metadata: Any = None, **kwargs
    ) -> GraphicCollection:
        """

        Create a collection of graphics of the same type.

        Parameters
        ----------
        data: list of array-like
            one entry per graphic; its length is the number of graphics in the collection

        name: str, optional
            name of the collection

        metadata: Any, optional
            metadata attached to the collection

        **kwargs
            any feature of the child graphic (``colors``, ``thickness``, ``sizes``, ...), each
            accepting one value for all graphics or one value per graphic. Any argument that is not
            a feature is passed unchanged to every child graphic.

        """
        return self._create_graphic(GraphicCollection, data, name, metadata, **kwargs)

    def add_image_collection(
        self,
        data: Any,
        vmin: float = None,
        vmax: float = None,
        cmap: str = "plasma",
        gamma: float = 1.0,
        interpolation: str = "nearest",
        cmap_interpolation: str = "linear",
        colorspace: ColorspacesRGB = "srgb",
        cpu_buffer: bool = True,
        *,
        name: str = None,
        metadata: Any = None,
        names=None,
        offsets=None,
        rotations=None,
        scales=None,
        alphas=None,
        alpha_modes=None,
        visibles=None,
        metadatas=None,
        **kwargs
    ) -> ImageCollection:
        """

        Create an ImageGraphic

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

        gamma: float, default 1.0
            gamma correction, the value scaled by ``vmin`` and ``vmax`` is raised to the power of ``gamma``

        interpolation: str, optional, default "nearest"
            interpolation filter, one of "nearest" or "linear"

        cmap_interpolation: str, optional, default "linear"
            colormap interpolation method, one of "nearest" or "linear"

        colorspace: one of "srgb", "tex-srgb", "physical", default "srgb"
            colorspace in which to interpret the provided data.

            * "srgb": the data represents intensity, rgb, or rgba pixels in the sRGB space.
              sRGB is a standard color space designed for consistent representation of colors
              across devices like monitors. Most images store colors in this space.
              The shader convers sRGB colors to physical in the shader before doing color computations.

            * "tex-srgb": the underlying texture will be of an sRGB format. This means the data
              is automatically converted to sRGB when it is sampled. This results in better glTF
              compliance (because interpolation in the sampling happens in linear space).
              Note that sampling *always* results in the sRGB values, also when not interpreted as color.
              Only supported for rgb and rgba data.

            * "physical": the colors are (already) in the physical / linear space, where lighting
              calculations can be applied. Shader code that interprets the data as color will use it as-is.

        cpu_buffer: bool, default True
            If ``True``, maintains a buffer of system RAM that is sychronized with a corresponding storage buffer
            on the GPU.
            If ``False``, setting the graphic data will send the new data directly to the GPU, we also
            call this "bufferless". This is much faster but lacks the following features:

            * you must update the entire data array, i.e. you can perform ``image.data = new_data``, and you
                cannot perform partial updates such as ``image.data[indices] = <new_data_at_indices>``.

            * RGB arrays of shape [rows, cols, 3] are not supported since wgpu does not have RGB textures,
                use RGBA or use `cpu_buffer=True` if you really need RGB instead of RGBA.

            * tooltip values for grayscale data are estimated using an inverse transforms on the colormap LUT.
                The tooltip values may or may not be accurate for a given colormap and vmin, vmax. If you require
                precise and reliable tooltip values for grayscale data use `cpu_buffer=True`.

            * vmin, vmax must be explicitly provided if sharing an existing buffer from another ImageGraphic
            * ``reset_vmin_vmax()`` is not supported
            * selector tools will not be able to return the data under the selection

        kwargs:
            additional keyword arguments passed to :class:`.Graphic`


        """
        return self._create_graphic(
            ImageCollection,
            data,
            vmin=vmin,
            vmax=vmax,
            cmap=cmap,
            gamma=gamma,
            interpolation=interpolation,
            cmap_interpolation=cmap_interpolation,
            colorspace=colorspace,
            cpu_buffer=cpu_buffer,
            name=name,
            metadata=metadata,
            names=names,
            offsets=offsets,
            rotations=rotations,
            scales=scales,
            alphas=alphas,
            alpha_modes=alpha_modes,
            visibles=visibles,
            metadatas=metadatas,
            **kwargs
        )

    def add_image(
        self,
        data: Any,
        vmin: float = None,
        vmax: float = None,
        cmap: str = "plasma",
        gamma: float = 1.0,
        interpolation: str = "nearest",
        cmap_interpolation: str = "linear",
        colorspace: ColorspacesRGB = "srgb",
        cpu_buffer: bool = True,
        **kwargs
    ) -> ImageGraphic:
        """

        Create an ImageGraphic

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

        gamma: float, default 1.0
            gamma correction, the value scaled by ``vmin`` and ``vmax`` is raised to the power of ``gamma``

        interpolation: str, optional, default "nearest"
            interpolation filter, one of "nearest" or "linear"

        cmap_interpolation: str, optional, default "linear"
            colormap interpolation method, one of "nearest" or "linear"

        colorspace: one of "srgb", "tex-srgb", "physical", default "srgb"
            colorspace in which to interpret the provided data.

            * "srgb": the data represents intensity, rgb, or rgba pixels in the sRGB space.
              sRGB is a standard color space designed for consistent representation of colors
              across devices like monitors. Most images store colors in this space.
              The shader convers sRGB colors to physical in the shader before doing color computations.

            * "tex-srgb": the underlying texture will be of an sRGB format. This means the data
              is automatically converted to sRGB when it is sampled. This results in better glTF
              compliance (because interpolation in the sampling happens in linear space).
              Note that sampling *always* results in the sRGB values, also when not interpreted as color.
              Only supported for rgb and rgba data.

            * "physical": the colors are (already) in the physical / linear space, where lighting
              calculations can be applied. Shader code that interprets the data as color will use it as-is.

        cpu_buffer: bool, default True
            If ``True``, maintains a buffer of system RAM that is sychronized with a corresponding storage buffer
            on the GPU.
            If ``False``, setting the graphic data will send the new data directly to the GPU, we also
            call this "bufferless". This is much faster but lacks the following features:

            * you must update the entire data array, i.e. you can perform ``image.data = new_data``, and you
                cannot perform partial updates such as ``image.data[indices] = <new_data_at_indices>``.

            * RGB arrays of shape [rows, cols, 3] are not supported since wgpu does not have RGB textures,
                use RGBA or use `cpu_buffer=True` if you really need RGB instead of RGBA.

            * tooltip values for grayscale data are estimated using an inverse transforms on the colormap LUT.
                The tooltip values may or may not be accurate for a given colormap and vmin, vmax. If you require
                precise and reliable tooltip values for grayscale data use `cpu_buffer=True`.

            * vmin, vmax must be explicitly provided if sharing an existing buffer from another ImageGraphic
            * ``reset_vmin_vmax()`` is not supported
            * selector tools will not be able to return the data under the selection

        kwargs:
            additional keyword arguments passed to :class:`.Graphic`


        """
        return self._create_graphic(
            ImageGraphic,
            data,
            vmin,
            vmax,
            cmap,
            gamma,
            interpolation,
            cmap_interpolation,
            colorspace,
            cpu_buffer,
            **kwargs
        )

    def add_image_grid(
        self,
        data: Any,
        vmin: float = None,
        vmax: float = None,
        cmap: str = "plasma",
        gamma: float = 1.0,
        interpolation: str = "nearest",
        cmap_interpolation: str = "linear",
        colorspace: ColorspacesRGB = "srgb",
        cpu_buffer: bool = True,
        *,
        shape: tuple[int, int] = None,
        separation: tuple[float, float] = (0.0, 0.0),
        offsets: np.ndarray = None,
        names=None,
        rotations=None,
        scales=None,
        alphas=None,
        alpha_modes=None,
        visibles=None,
        metadatas=None,
        **kwargs
    ) -> ImageGrid:
        """

        Create an ImageGraphic

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

        gamma: float, default 1.0
            gamma correction, the value scaled by ``vmin`` and ``vmax`` is raised to the power of ``gamma``

        interpolation: str, optional, default "nearest"
            interpolation filter, one of "nearest" or "linear"

        cmap_interpolation: str, optional, default "linear"
            colormap interpolation method, one of "nearest" or "linear"

        colorspace: one of "srgb", "tex-srgb", "physical", default "srgb"
            colorspace in which to interpret the provided data.

            * "srgb": the data represents intensity, rgb, or rgba pixels in the sRGB space.
              sRGB is a standard color space designed for consistent representation of colors
              across devices like monitors. Most images store colors in this space.
              The shader convers sRGB colors to physical in the shader before doing color computations.

            * "tex-srgb": the underlying texture will be of an sRGB format. This means the data
              is automatically converted to sRGB when it is sampled. This results in better glTF
              compliance (because interpolation in the sampling happens in linear space).
              Note that sampling *always* results in the sRGB values, also when not interpreted as color.
              Only supported for rgb and rgba data.

            * "physical": the colors are (already) in the physical / linear space, where lighting
              calculations can be applied. Shader code that interprets the data as color will use it as-is.

        cpu_buffer: bool, default True
            If ``True``, maintains a buffer of system RAM that is sychronized with a corresponding storage buffer
            on the GPU.
            If ``False``, setting the graphic data will send the new data directly to the GPU, we also
            call this "bufferless". This is much faster but lacks the following features:

            * you must update the entire data array, i.e. you can perform ``image.data = new_data``, and you
                cannot perform partial updates such as ``image.data[indices] = <new_data_at_indices>``.

            * RGB arrays of shape [rows, cols, 3] are not supported since wgpu does not have RGB textures,
                use RGBA or use `cpu_buffer=True` if you really need RGB instead of RGBA.

            * tooltip values for grayscale data are estimated using an inverse transforms on the colormap LUT.
                The tooltip values may or may not be accurate for a given colormap and vmin, vmax. If you require
                precise and reliable tooltip values for grayscale data use `cpu_buffer=True`.

            * vmin, vmax must be explicitly provided if sharing an existing buffer from another ImageGraphic
            * ``reset_vmin_vmax()`` is not supported
            * selector tools will not be able to return the data under the selection

        kwargs:
            additional keyword arguments passed to :class:`.Graphic`


        """
        return self._create_graphic(
            ImageGrid,
            data,
            vmin=vmin,
            vmax=vmax,
            cmap=cmap,
            gamma=gamma,
            interpolation=interpolation,
            cmap_interpolation=cmap_interpolation,
            colorspace=colorspace,
            cpu_buffer=cpu_buffer,
            shape=shape,
            separation=separation,
            offsets=offsets,
            names=names,
            rotations=rotations,
            scales=scales,
            alphas=alphas,
            alpha_modes=alpha_modes,
            visibles=visibles,
            metadatas=metadatas,
            **kwargs
        )

    def add_image_volume(
        self,
        data: Any,
        mode: str = "mip",
        vmin: float = None,
        vmax: float = None,
        cmap: str = "plasma",
        gamma: float = 1.0,
        interpolation: str = "linear",
        cmap_interpolation: str = "linear",
        plane: tuple[float, float, float, float] = (0, 0, -1, 0),
        threshold: float = 0.5,
        step_size: float = 1.0,
        substep_size: float = 0.1,
        emissive: str | tuple | np.ndarray = (0, 0, 0),
        shininess: int = 30,
        **kwargs
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

        gamma: float, default 1.0
            gamma correction, the value scaled by ``vmin`` and ``vmax`` is raised to the power of ``gamma``

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
            gamma,
            interpolation,
            cmap_interpolation,
            plane,
            threshold,
            step_size,
            substep_size,
            emissive,
            shininess,
            **kwargs
        )

    def add_image_yuv(
        self,
        data: TupleYUV | TextureYUV,
        vmin: float = 0,
        vmax: float = 255,
        gamma: float = 1.0,
        interpolation: str = "nearest",
        colorspace: ColorspacesYUV = "yuv420p",
        colorrange: ColorRange = "limited",
        **kwargs
    ) -> ImageYUVGraphic:
        """

        Create an ImageYUVGraphic. Similar to ImageGraphic but handles data that is in yuv42p or yuv444p colorspace.

        Note that the buffers for YUV Images only exist on the GPU. When setting the image data, the new values are
        directly sent to the GPU.

        ``reset_vmin_vmax()`` just sets (vmin, vmax) to (0, 255)

        Parameters
        ----------
        data: TupleYUV
            tuple of arrays that represent YUV channels. If the colorspace is yuv420p, the U and V array dims
            must be 4 times smaller than the Y array dims.

        vmin: float, optional, default 0
            minimum value for color scaling

        vmax: float, optional, default 255
            maximum value for color scaling

        gamma: float, default 1.0
            gamma correction, the value scaled by ``vmin`` and ``vmax`` is raised to the power of ``gamma``

        interpolation: str, optional, default "nearest"
            interpolation filter, one of "nearest" or "linear"

        colorspace: "yuv42p" | "yuv444p"
            colorspace in which to interpret the provided data.

            * "yuv420p": A common video format. The data is represented as 3 planes (y, u, and v).
              The y represents intensity, and is at full resolution. The u and v planes are a
              quarter of the size.

            * "yuv444p": A lesser common video format. The data is represented as 3 planes
              (y, u, and v) similar to yuv420p however the u and v planes are stored
              at full resolution.

        colorrange: Literal["full", "limited"] = "limited",
            Relevant for yuv colorspaces. Most videos use "limited".

            * "limited": The luma plane (Y) is limited to the range of 16-235 for 8 bits.
              The chroma planes (U and V) are limited to the range of 16-240 for 8 bits
            * "full": The luma plane and chroma plane use the full range of the storage format.

            See the following links from the FFMPEG documentation for more details:
            https://trac.ffmpeg.org/wiki/colorspace
            https://ffmpeg.org/doxygen/7.0/pixfmt_8h_source.html#l00609

        cpu_buffer: bool, default True
            If ``True``, maintains a buffer of system RAM that is sychronized with a corresponding storage buffer
            on the GPU.
            If ``False``, setting the graphic data will send the new data directly to the GPU, we also
            call this "bufferless". This is much faster but lacks the following features:

            * you must update the entire data array, i.e. you can perform ``image.data = new_data``, and you
                cannot perform partial updates such as ``image.data[indices] = <new_data_at_indices>``.

            * RGB arrays of shape [rows, cols, 3] are not supported since wgpu does not have RGB textures,
                use RGBA or use `cpu_buffer=True` if you really need RGB instead of RGBA.

            * tooltip values for grayscale data are estimated using an inverse transforms on the colormap LUT.
                The tooltip values may or may not be accurate for a given colormap and vmin, vmax. If you require
                precise and reliable tooltip values for grayscale data use `cpu_buffer=True`.

        kwargs:
            additional keyword arguments passed to :class:`.Graphic`


        """
        return self._create_graphic(
            ImageYUVGraphic,
            data,
            vmin,
            vmax,
            gamma,
            interpolation,
            colorspace,
            colorrange,
            **kwargs
        )

    def add_inf_line(
        self,
        data: Any,
        axis: Literal["x", "y", "z"] | None = None,
        thickness: float = 2.0,
        colors: ColorLike | MultiColorLike = "w",
        cmap: ColormapLike = None,
        cmap_transform: np.ndarray | None = None,
        cmap_range: tuple[float, float] | None = None,
        start_is_infinite: bool = True,
        end_is_infinite: bool = True,
        dash_pattern: str | tuple | list = (),
        size_space: str = "screen",
        **kwargs
    ) -> InfLineGraphic:
        """

        Create a collection of infinite lines.

        Parameters
        ----------
        data: array-like
            The line positions. If ``axis`` is "x", "y", or "z", a 1D array of positions along
            that axis; one infinite line is drawn at each position. If ``axis`` is None, ``data``
            is used directly as the segment endpoints, of shape [n_points, 2 | 3], where every two
            consecutive points define one line.

        axis: "x", "y", "z", or None, default None
            The axis along which the line positions are given. If None, ``data`` is interpreted
            directly as the segment endpoints.

        thickness: float, optional, default 2.0
            thickness of the lines

        colors: ColorLike or MultiColorLike, default "w"
            specify colors as a single human-readable string, a single RGBA array, or a Sequence
            (array, tuple, or list) of strings or RGBA arrays. A sequence of colors provides one
            color per line.

        cmap: str, optional
            Apply a colormap to the lines instead of assigning colors manually, one color per line.
            This overrides any argument passed to "colors". For supported colormaps see the
            ``cmap`` library catalogue: https://cmap-docs.readthedocs.io/en/stable/catalog/

        cmap_transform: 1D array-like of numerical values, optional
            if provided, these values are used to map the colors from the cmap

        cmap_range: (float, float), optional
            the (min, max) of the cmap_transform mapped onto the colormap, defaults to the transform's own range

        start_is_infinite: bool, default True
            whether the start of each line is extended to infinity

        end_is_infinite: bool, default True
            whether the end of each line is extended to infinity

        dash_pattern: str, tuple, or list, default ()
            The dash pattern. May be a matplotlib-style string, one of ``"-", "--", "-.", ":"``
            or ``"solid", "dashed", "dashdot", "dotted"``, or a sequence of floats describing the
            length of strokes and gaps.

        size_space: str, default "screen"
            coordinate space in which the thickness is expressed ("screen", "world", "model")

        **kwargs
            passed to :class:`.Graphic`


        """
        return self._create_graphic(
            InfLineGraphic,
            data,
            axis,
            thickness,
            colors,
            cmap,
            cmap_transform,
            cmap_range,
            start_is_infinite,
            end_is_infinite,
            dash_pattern,
            size_space,
            **kwargs
        )

    def add_line_collection(
        self,
        data: Any,
        thickness: float = 2.0,
        colors: ColorLike | MultiColorLike = "w",
        cmap: ColormapLike | None = None,
        cmap_transform: np.ndarray | Iterable[int | float] | None = None,
        cmap_range: tuple[float, float] | None = None,
        size_space: str = "screen",
        dash_pattern: str | tuple | list = (),
        thin: bool = False,
        *,
        names=None,
        offsets=None,
        rotations=None,
        scales=None,
        alphas=None,
        alpha_modes=None,
        visibles=None,
        metadatas=None,
        **kwargs
    ) -> LineCollection:
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

        colors: ColorLike or MultiColorLike, default "w"
            specify colors as a single human-readable string, a single RGBA array,
            or a Sequence (array, tuple, or list) of strings or RGBA arrays

        cmap: ColormapLike, optional
            Apply a colormap to the line instead of assigning colors manually, this
            overrides any argument passed to "colors". For supported colormaps see the
            ``cmap`` library catalogue: https://cmap-docs.readthedocs.io/en/stable/catalog/

        cmap_transform: 1D array-like of numerical values, optional
            if provided, these values are used to map the colors from the cmap

        cmap_range: (float, float), optional
            the (min, max) of the cmap_transform mapped onto the colormap, defaults to the transform's own range

        size_space: str, default "screen"
            coordinate space in which the thickness is expressed ("screen", "world", "model")

        dash_pattern: str, tuple, or list, default ()
            The dash pattern. May be a matplotlib-style string, one of ``"-", "--", "-.", ":"``
            or ``"solid", "dashed", "dashdot", "dotted"``, or a sequence of floats describing the
            length of strokes and gaps. Ignored when ``thin`` is True.

        thin: bool, default False
            Use the more performant thin line material, which is always one physical pixel wide.
            Thickness, dashing, and anti-aliasing are ignored when True.

        **kwargs
            passed to :class:`.Graphic`


        """
        return self._create_graphic(
            LineCollection,
            data,
            thickness=thickness,
            colors=colors,
            cmap=cmap,
            cmap_transform=cmap_transform,
            cmap_range=cmap_range,
            size_space=size_space,
            dash_pattern=dash_pattern,
            thin=thin,
            names=names,
            offsets=offsets,
            rotations=rotations,
            scales=scales,
            alphas=alphas,
            alpha_modes=alpha_modes,
            visibles=visibles,
            metadatas=metadatas,
            **kwargs
        )

    def add_line(
        self,
        data: Any,
        thickness: float = 2.0,
        colors: ColorLike | MultiColorLike = "w",
        cmap: ColormapLike | None = None,
        cmap_transform: np.ndarray | Iterable[int | float] | None = None,
        cmap_range: tuple[float, float] | None = None,
        size_space: str = "screen",
        dash_pattern: str | tuple | list = (),
        thin: bool = False,
        **kwargs
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

        colors: ColorLike or MultiColorLike, default "w"
            specify colors as a single human-readable string, a single RGBA array,
            or a Sequence (array, tuple, or list) of strings or RGBA arrays

        cmap: ColormapLike, optional
            Apply a colormap to the line instead of assigning colors manually, this
            overrides any argument passed to "colors". For supported colormaps see the
            ``cmap`` library catalogue: https://cmap-docs.readthedocs.io/en/stable/catalog/

        cmap_transform: 1D array-like of numerical values, optional
            if provided, these values are used to map the colors from the cmap

        cmap_range: (float, float), optional
            the (min, max) of the cmap_transform mapped onto the colormap, defaults to the transform's own range

        size_space: str, default "screen"
            coordinate space in which the thickness is expressed ("screen", "world", "model")

        dash_pattern: str, tuple, or list, default ()
            The dash pattern. May be a matplotlib-style string, one of ``"-", "--", "-.", ":"``
            or ``"solid", "dashed", "dashdot", "dotted"``, or a sequence of floats describing the
            length of strokes and gaps. Ignored when ``thin`` is True.

        thin: bool, default False
            Use the more performant thin line material, which is always one physical pixel wide.
            Thickness, dashing, and anti-aliasing are ignored when True.

        **kwargs
            passed to :class:`.Graphic`


        """
        return self._create_graphic(
            LineGraphic,
            data,
            thickness,
            colors,
            cmap,
            cmap_transform,
            cmap_range,
            size_space,
            dash_pattern,
            thin,
            **kwargs
        )

    def add_line_stack(
        self,
        data: Any,
        thickness: float = 2.0,
        colors: ColorLike | MultiColorLike = "w",
        cmap: ColormapLike | None = None,
        cmap_transform: np.ndarray | Iterable[int | float] | None = None,
        cmap_range: tuple[float, float] | None = None,
        size_space: str = "screen",
        dash_pattern: str | tuple | list = (),
        thin: bool = False,
        *,
        separation: tuple[float, float, float] = (0.0, 0.0, 0.0),
        separation_axis: str = "y",
        steps: np.ndarray = None,
        names=None,
        offsets=None,
        rotations=None,
        scales=None,
        alphas=None,
        alpha_modes=None,
        visibles=None,
        metadatas=None,
        **kwargs
    ) -> LineStack:
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

        colors: ColorLike or MultiColorLike, default "w"
            specify colors as a single human-readable string, a single RGBA array,
            or a Sequence (array, tuple, or list) of strings or RGBA arrays

        cmap: ColormapLike, optional
            Apply a colormap to the line instead of assigning colors manually, this
            overrides any argument passed to "colors". For supported colormaps see the
            ``cmap`` library catalogue: https://cmap-docs.readthedocs.io/en/stable/catalog/

        cmap_transform: 1D array-like of numerical values, optional
            if provided, these values are used to map the colors from the cmap

        cmap_range: (float, float), optional
            the (min, max) of the cmap_transform mapped onto the colormap, defaults to the transform's own range

        size_space: str, default "screen"
            coordinate space in which the thickness is expressed ("screen", "world", "model")

        dash_pattern: str, tuple, or list, default ()
            The dash pattern. May be a matplotlib-style string, one of ``"-", "--", "-.", ":"``
            or ``"solid", "dashed", "dashdot", "dotted"``, or a sequence of floats describing the
            length of strokes and gaps. Ignored when ``thin`` is True.

        thin: bool, default False
            Use the more performant thin line material, which is always one physical pixel wide.
            Thickness, dashing, and anti-aliasing are ignored when True.

        **kwargs
            passed to :class:`.Graphic`


        """
        return self._create_graphic(
            LineStack,
            data,
            thickness=thickness,
            colors=colors,
            cmap=cmap,
            cmap_transform=cmap_transform,
            cmap_range=cmap_range,
            size_space=size_space,
            dash_pattern=dash_pattern,
            thin=thin,
            separation=separation,
            separation_axis=separation_axis,
            steps=steps,
            names=names,
            offsets=offsets,
            rotations=rotations,
            scales=scales,
            alphas=alphas,
            alpha_modes=alpha_modes,
            visibles=visibles,
            metadatas=metadatas,
            **kwargs
        )

    def add_mesh(
        self,
        positions: Any,
        indices: Any,
        mode: Literal["basic", "phong", "slice"] = "phong",
        plane: tuple[float, float, float, float] = (0.0, 0.0, 1.0, 0.0),
        colors: str | np.ndarray | Sequence = "w",
        mapcoords: Any = None,
        cmap: str | dict | pygfx.Texture | pygfx.TextureMap | np.ndarray = None,
        clim: tuple[float, float] = None,
        **kwargs
    ) -> MeshGraphic:
        """

        Create a mesh Graphic.

        Parameters
        ----------
        positions: array-like
            The 3D positions of the vertices.

        indices: array-like
            The indices into the positions that make up the triangles. Each 3
            subsequent indices form a triangle.

        mode: one of "basic", "phong", "slice", default "phong"
            * basic: illuminate mesh with only ambient lighting
            * phong: phong lighting model, good for most use cases, see https://en.wikipedia.org/wiki/Phong_shading
            * slice: display a slice of the mesh at the specified ``plane``

        plane: (float, float, float, float), default (0., 0., 1., 0.)
            Slice mesh at this plane. Sets (a, b, c, d) in the equation the defines a plane: ax + by + cz + d = 0.
            Used only if `mode` = "slice". The plane is defined in world space.

        colors: str, array, or iterable, default "w"
            A uniform color, or the per-position colors.

        mapcoords: array-like
            The per-position coordinates to which to apply the colormap (a.k.a. texcoords).
            These can e.g. be some domain-specific value, mapped to [0..1].
            If ``mapcoords`` and ``cmap`` are given, they are used instead of ``colors``.

        cmap: str, optional
            Apply a colormap to the mesh, this overrides any argument passed to
            "colors". For supported colormaps see the ``cmap`` library
            catalogue: https://cmap-docs.readthedocs.io/en/stable/catalog/
            Both 1D and 2D colormaps are supported, though the mapcoords has to match the dimensionality.
            An image can also be used, this is basically a 2D colormap.

        **kwargs
            passed to :class:`.Graphic`


        """
        return self._create_graphic(
            MeshGraphic,
            positions,
            indices,
            mode,
            plane,
            colors,
            mapcoords,
            cmap,
            clim,
            **kwargs
        )

    def add_polygon(
        self,
        data: np.ndarray,
        mode: Literal["basic", "phong"] = "basic",
        colors: str | np.ndarray | Sequence = "w",
        mapcoords: Any = None,
        cmap: str | dict | pygfx.Texture | pygfx.TextureMap | np.ndarray = None,
        clim: tuple[float, float] | None = None,
        **kwargs
    ) -> PolygonGraphic:
        """

        Create a polygon mesh graphic.

        The data are always in the 'xy' plane. Set a rotation to display the polygon in another plane or in 3D space.

        Parameters
        ----------
        data: array-like
            The polygon vertices, must be of shape: [n_vertices, 2]

        mode: one of "basic", "phong", "slice", default "phong"
            * basic: illuminate mesh with only ambient lighting
            * phong: phong lighting model, good for most use cases, see https://en.wikipedia.org/wiki/Phong_shading

        colors: str, array, or iterable, default "w"
            A uniform color, or the per-position colors.

        mapcoords: array-like
            The per-position coordinates to which to apply the colormap (a.k.a. texcoords).
            These can e.g. be some domain-specific value (mapped to [0..1] using ``clim``).
            If not given, they will be the depth (z-coordinate) of the surface.

        cmap: str, optional
            Apply a colormap to the mesh, this overrides any argument passed to
            "colors". For supported colormaps see the ``cmap`` library
            catalogue: https://cmap-docs.readthedocs.io/en/stable/catalog/
            Both 1D and 2D colormaps are supported, though the mapcoords has to match the dimensionality.

        clim: tuple[float, float]
            The colormap limits. If the mapcoords has values between e.g. 5 and 90, you want to set the clim
            to e.g. (5, 90) or (0, 100) to determine how the values map onto the colormap.

        **kwargs
             passed to :class:`.Graphic`

        """
        return self._create_graphic(
            PolygonGraphic, data, mode, colors, mapcoords, cmap, clim, **kwargs
        )

    def add_scatter_collection(
        self,
        data: Any,
        colors: ColorLike | MultiColorLike = "w",
        cmap: ColormapLike | None = None,
        cmap_transform: np.ndarray | None = None,
        cmap_range: tuple[float, float] | None = None,
        mode: Literal["markers", "simple", "gaussian", "image"] = "markers",
        markers: str | np.ndarray | Sequence[str] = "o",
        custom_sdf: str = None,
        edge_colors: ColorLike | MultiColorLike | None = "black",
        edge_width: float = 1.0,
        image: np.ndarray = None,
        point_rotations: float | np.ndarray | None = None,
        sizes: float | np.ndarray | Sequence[float] = 5,
        size_space: str = "screen",
        *,
        names=None,
        offsets=None,
        rotations=None,
        scales=None,
        alphas=None,
        alpha_modes=None,
        visibles=None,
        metadatas=None,
        **kwargs
    ) -> ScatterCollection:
        """

        Create a Scatter Graphic, 2d or 3d

        Parameters
        ----------
        data: array-like
            Scatter data to plot, Can provide 2D, or a 3D data. 2D data must be of shape [n_points, 2].
            3D data must be of shape [n_points, 3]

        colors: ColorLike or MultiColorLike, default "w"
            specify colors as a single human-readable string, a single RGBA array,
            or a Sequence (array, tuple, or list) of strings or RGBA arrays

        cmap: ColormapLike, optional
            apply a colormap to the scatter instead of assigning colors manually, this
            overrides any argument passed to "colors".
            For supported colormaps see the ``cmap`` library catalogue:
            https://cmap-docs.readthedocs.io/en/stable/catalog/

        cmap_transform: np.ndarray, optional
            1D array-like or list of numerical values, these values are used to map the colors from the cmap

        cmap_range: (float, float), optional
            the (min, max) of the cmap_transform mapped onto the colormap, defaults to the transform's own range

        mode: one of: "markers", "simple", "gaussian", "image", default "markers"
            The scatter points mode, cannot be changed after the graphic has been created.

            * markers: represent points with various or custom markers, default
            * simple: all scatters points are simple circles
            * gaussian: each point is a gaussian blob
            * image: use an image for each point, pass an array to the `image` kwarg, these are also called sprites

        markers: str | np.ndarray | Sequence[str], default "o"
            The shape of the markers when `mode` is "markers". Specify a single marker to use the same
            marker for all points, or a Sequence of markers for per-vertex markers.

            Supported values:

            * A string from pygfx.MarkerShape enum
            * Matplotlib compatible characters: "osD+x^v<>*".
            * Unicode symbols: "●○■♦♥♠♣✳▲▼◀▶".
            * Emojis: "❤️♠️♣️♦️💎💍✳️📍".
            * A string containing the value "custom". In this case, WGSL code defined by ``custom_sdf`` will be used.

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

        edge_colors: ColorLike, MultiColorLike, or None, default "black"
            edge color(s) of the markers, used when `mode` is "markers". Specify a single color to use the
            same edge color for all markers, or a Sequence of colors for per-vertex edge colors. Pass
            ``None`` for no edge color.

        edge_width: float = 1.0,
            Width of the marker edges. used when `mode` is "markers".

        image: array-like, optional
            renders an image at the scatter points, also known as sprites.
            The image color is multiplied with the point's "normal" color.

        point_rotations: float, array-like, or None, default None
            The rotation of the scatter points in radians. The rotation mode is determined automatically from
            the value: pass ``None`` (default) for "curve" mode, where each point's rotation follows the curve
            of the data (in screen space); a single float for the same rotation on every point ("uniform"); or
            an array of rotation values for per-point rotations ("vertex").

        sizes: float, np.ndarray, or Sequence[float], default 5
            size(s) of the scatter points. Specify a single size to use the same size for all points, or a
            Sequence of sizes for per-point sizes.

        size_space: str, default "screen"
            coordinate space in which the size is expressed, one of ("screen", "world", "model")

        kwargs
            passed to :class:`.Graphic`


        """
        return self._create_graphic(
            ScatterCollection,
            data,
            colors=colors,
            cmap=cmap,
            cmap_transform=cmap_transform,
            cmap_range=cmap_range,
            mode=mode,
            markers=markers,
            custom_sdf=custom_sdf,
            edge_colors=edge_colors,
            edge_width=edge_width,
            image=image,
            point_rotations=point_rotations,
            sizes=sizes,
            size_space=size_space,
            names=names,
            offsets=offsets,
            rotations=rotations,
            scales=scales,
            alphas=alphas,
            alpha_modes=alpha_modes,
            visibles=visibles,
            metadatas=metadatas,
            **kwargs
        )

    def add_scatter(
        self,
        data: Any,
        colors: ColorLike | MultiColorLike = "w",
        cmap: ColormapLike | None = None,
        cmap_transform: np.ndarray | None = None,
        cmap_range: tuple[float, float] | None = None,
        mode: Literal["markers", "simple", "gaussian", "image"] = "markers",
        markers: str | np.ndarray | Sequence[str] = "o",
        custom_sdf: str = None,
        edge_colors: ColorLike | MultiColorLike | None = "black",
        edge_width: float = 1.0,
        image: np.ndarray = None,
        point_rotations: float | np.ndarray | None = None,
        sizes: float | np.ndarray | Sequence[float] = 5,
        size_space: str = "screen",
        **kwargs
    ) -> ScatterGraphic:
        """

        Create a Scatter Graphic, 2d or 3d

        Parameters
        ----------
        data: array-like
            Scatter data to plot, Can provide 2D, or a 3D data. 2D data must be of shape [n_points, 2].
            3D data must be of shape [n_points, 3]

        colors: ColorLike or MultiColorLike, default "w"
            specify colors as a single human-readable string, a single RGBA array,
            or a Sequence (array, tuple, or list) of strings or RGBA arrays

        cmap: ColormapLike, optional
            apply a colormap to the scatter instead of assigning colors manually, this
            overrides any argument passed to "colors".
            For supported colormaps see the ``cmap`` library catalogue:
            https://cmap-docs.readthedocs.io/en/stable/catalog/

        cmap_transform: np.ndarray, optional
            1D array-like or list of numerical values, these values are used to map the colors from the cmap

        cmap_range: (float, float), optional
            the (min, max) of the cmap_transform mapped onto the colormap, defaults to the transform's own range

        mode: one of: "markers", "simple", "gaussian", "image", default "markers"
            The scatter points mode, cannot be changed after the graphic has been created.

            * markers: represent points with various or custom markers, default
            * simple: all scatters points are simple circles
            * gaussian: each point is a gaussian blob
            * image: use an image for each point, pass an array to the `image` kwarg, these are also called sprites

        markers: str | np.ndarray | Sequence[str], default "o"
            The shape of the markers when `mode` is "markers". Specify a single marker to use the same
            marker for all points, or a Sequence of markers for per-vertex markers.

            Supported values:

            * A string from pygfx.MarkerShape enum
            * Matplotlib compatible characters: "osD+x^v<>*".
            * Unicode symbols: "●○■♦♥♠♣✳▲▼◀▶".
            * Emojis: "❤️♠️♣️♦️💎💍✳️📍".
            * A string containing the value "custom". In this case, WGSL code defined by ``custom_sdf`` will be used.

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

        edge_colors: ColorLike, MultiColorLike, or None, default "black"
            edge color(s) of the markers, used when `mode` is "markers". Specify a single color to use the
            same edge color for all markers, or a Sequence of colors for per-vertex edge colors. Pass
            ``None`` for no edge color.

        edge_width: float = 1.0,
            Width of the marker edges. used when `mode` is "markers".

        image: array-like, optional
            renders an image at the scatter points, also known as sprites.
            The image color is multiplied with the point's "normal" color.

        point_rotations: float, array-like, or None, default None
            The rotation of the scatter points in radians. The rotation mode is determined automatically from
            the value: pass ``None`` (default) for "curve" mode, where each point's rotation follows the curve
            of the data (in screen space); a single float for the same rotation on every point ("uniform"); or
            an array of rotation values for per-point rotations ("vertex").

        sizes: float, np.ndarray, or Sequence[float], default 5
            size(s) of the scatter points. Specify a single size to use the same size for all points, or a
            Sequence of sizes for per-point sizes.

        size_space: str, default "screen"
            coordinate space in which the size is expressed, one of ("screen", "world", "model")

        kwargs
            passed to :class:`.Graphic`


        """
        return self._create_graphic(
            ScatterGraphic,
            data,
            colors,
            cmap,
            cmap_transform,
            cmap_range,
            mode,
            markers,
            custom_sdf,
            edge_colors,
            edge_width,
            image,
            point_rotations,
            sizes,
            size_space,
            **kwargs
        )

    def add_scatter_stack(
        self,
        data: Any,
        colors: ColorLike | MultiColorLike = "w",
        cmap: ColormapLike | None = None,
        cmap_transform: np.ndarray | None = None,
        cmap_range: tuple[float, float] | None = None,
        mode: Literal["markers", "simple", "gaussian", "image"] = "markers",
        markers: str | np.ndarray | Sequence[str] = "o",
        custom_sdf: str = None,
        edge_colors: ColorLike | MultiColorLike | None = "black",
        edge_width: float = 1.0,
        image: np.ndarray = None,
        point_rotations: float | np.ndarray | None = None,
        sizes: float | np.ndarray | Sequence[float] = 5,
        size_space: str = "screen",
        *,
        separation: tuple[float, float, float] = (0.0, 0.0, 0.0),
        separation_axis: str = "y",
        steps: np.ndarray = None,
        names=None,
        offsets=None,
        rotations=None,
        scales=None,
        alphas=None,
        alpha_modes=None,
        visibles=None,
        metadatas=None,
        **kwargs
    ) -> ScatterStack:
        """

        Create a Scatter Graphic, 2d or 3d

        Parameters
        ----------
        data: array-like
            Scatter data to plot, Can provide 2D, or a 3D data. 2D data must be of shape [n_points, 2].
            3D data must be of shape [n_points, 3]

        colors: ColorLike or MultiColorLike, default "w"
            specify colors as a single human-readable string, a single RGBA array,
            or a Sequence (array, tuple, or list) of strings or RGBA arrays

        cmap: ColormapLike, optional
            apply a colormap to the scatter instead of assigning colors manually, this
            overrides any argument passed to "colors".
            For supported colormaps see the ``cmap`` library catalogue:
            https://cmap-docs.readthedocs.io/en/stable/catalog/

        cmap_transform: np.ndarray, optional
            1D array-like or list of numerical values, these values are used to map the colors from the cmap

        cmap_range: (float, float), optional
            the (min, max) of the cmap_transform mapped onto the colormap, defaults to the transform's own range

        mode: one of: "markers", "simple", "gaussian", "image", default "markers"
            The scatter points mode, cannot be changed after the graphic has been created.

            * markers: represent points with various or custom markers, default
            * simple: all scatters points are simple circles
            * gaussian: each point is a gaussian blob
            * image: use an image for each point, pass an array to the `image` kwarg, these are also called sprites

        markers: str | np.ndarray | Sequence[str], default "o"
            The shape of the markers when `mode` is "markers". Specify a single marker to use the same
            marker for all points, or a Sequence of markers for per-vertex markers.

            Supported values:

            * A string from pygfx.MarkerShape enum
            * Matplotlib compatible characters: "osD+x^v<>*".
            * Unicode symbols: "●○■♦♥♠♣✳▲▼◀▶".
            * Emojis: "❤️♠️♣️♦️💎💍✳️📍".
            * A string containing the value "custom". In this case, WGSL code defined by ``custom_sdf`` will be used.

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

        edge_colors: ColorLike, MultiColorLike, or None, default "black"
            edge color(s) of the markers, used when `mode` is "markers". Specify a single color to use the
            same edge color for all markers, or a Sequence of colors for per-vertex edge colors. Pass
            ``None`` for no edge color.

        edge_width: float = 1.0,
            Width of the marker edges. used when `mode` is "markers".

        image: array-like, optional
            renders an image at the scatter points, also known as sprites.
            The image color is multiplied with the point's "normal" color.

        point_rotations: float, array-like, or None, default None
            The rotation of the scatter points in radians. The rotation mode is determined automatically from
            the value: pass ``None`` (default) for "curve" mode, where each point's rotation follows the curve
            of the data (in screen space); a single float for the same rotation on every point ("uniform"); or
            an array of rotation values for per-point rotations ("vertex").

        sizes: float, np.ndarray, or Sequence[float], default 5
            size(s) of the scatter points. Specify a single size to use the same size for all points, or a
            Sequence of sizes for per-point sizes.

        size_space: str, default "screen"
            coordinate space in which the size is expressed, one of ("screen", "world", "model")

        kwargs
            passed to :class:`.Graphic`


        """
        return self._create_graphic(
            ScatterStack,
            data,
            colors=colors,
            cmap=cmap,
            cmap_transform=cmap_transform,
            cmap_range=cmap_range,
            mode=mode,
            markers=markers,
            custom_sdf=custom_sdf,
            edge_colors=edge_colors,
            edge_width=edge_width,
            image=image,
            point_rotations=point_rotations,
            sizes=sizes,
            size_space=size_space,
            separation=separation,
            separation_axis=separation_axis,
            steps=steps,
            names=names,
            offsets=offsets,
            rotations=rotations,
            scales=scales,
            alphas=alphas,
            alpha_modes=alpha_modes,
            visibles=visibles,
            metadatas=metadatas,
            **kwargs
        )

    def add_surface(
        self,
        data: np.ndarray,
        mode: Literal["basic", "phong", "slice"] = "phong",
        colors: str | np.ndarray | Sequence = "w",
        mapcoords: Any = None,
        cmap: str | dict | pygfx.Texture | pygfx.TextureMap | np.ndarray = None,
        clim: tuple[float, float] | None = None,
        **kwargs
    ) -> SurfaceGraphic:
        """

        Create a Surface mesh Graphic

        Parameters
        ----------
        data: array-like
            A height-map (an image where the values indicate height, i.e. z values).
            Can also be a [m, n, 3] to explicitly specify the x and y values in addition to the z values.
            [m, n, 3] is a dstack of (x, y, z) values that form a grid on the xy plane.

        mode: one of "basic", "phong", "slice", default "phong"
            * basic: illuminate mesh with only ambient lighting
            * phong: phong lighting model, good for most use cases, see https://en.wikipedia.org/wiki/Phong_shading

        colors: str, array, or iterable, default "w"
            A uniform color, or the per-position colors.

        mapcoords: array-like
            The per-position coordinates to which to apply the colormap (a.k.a. texcoords).
            These can e.g. be some domain-specific value (mapped to [0..1] using ``clim``).
            If not given, they will be the depth (z-coordinate) of the surface.

        cmap: str, optional
            Apply a colormap to the mesh, this overrides any argument passed to
            "colors". For supported colormaps see the ``cmap`` library
            catalogue: https://cmap-docs.readthedocs.io/en/stable/catalog/
            Both 1D and 2D colormaps are supported, though the mapcoords has to match the dimensionality.

        clim: tuple[float, float]
            The colormap limits. If the mapcoords has values between e.g. 5 and 90, you want to set the clim
            to e.g. (5, 90) or (0, 100) to determine how the values map onto the colormap.

        **kwargs
             passed to :class:`.Graphic`


        """
        return self._create_graphic(
            SurfaceGraphic, data, mode, colors, mapcoords, cmap, clim, **kwargs
        )

    def add_text(
        self,
        text: str,
        font_size: float | int = 14,
        face_color: str | np.ndarray | list[float] | tuple[float] = "w",
        outline_color: str | np.ndarray | list[float] | tuple[float] = "w",
        outline_thickness: float = 0.0,
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
            **kwargs
        )

    def add_vectors(
        self,
        positions: np.ndarray | Sequence[float],
        directions: np.ndarray | Sequence[float],
        color: str | Sequence[float] | np.ndarray = "w",
        size: float = None,
        vector_shape_options: dict = None,
        **kwargs
    ) -> VectorsGraphic:
        """

        Create graphic that draw vectors. Similar to matplotlib quiver.

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
            Estimated from density if not provided.

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
            VectorsGraphic,
            positions,
            directions,
            color,
            size,
            vector_shape_options,
            **kwargs
        )
