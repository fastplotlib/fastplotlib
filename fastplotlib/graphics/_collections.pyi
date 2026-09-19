# This is an auto-generated file and should not be modified directly
# regenerate with: python scripts/generate_graphics_stubs.py

from fastplotlib.graphics.line import *
from fastplotlib.graphics.scatter import *
from fastplotlib.graphics.image import *
from fastplotlib.graphics._collection_base import GraphicCollection
from fastplotlib.graphics._jagged_array import (
    CollectionColors,
    CollectionFeatureAccessor,
    JaggedCollectionFeature,
)
from fastplotlib.graphics.selectors import (
    LinearSelector,
    LinearRegionSelector,
    RectangleSelector,
    PolygonSelector,
)

class PositionsCollection(GraphicCollection):
    @property
    def cmap(self) -> str | list | None:
        """

        get or set the colormap(s) across the collection

        A single colormap gives each graphic one color, spread across the colormap. An iterable of
        colormaps gives each graphic its own colormap along its datapoints.

        """

    @cmap.setter
    def cmap(self, value): ...
    @property
    def cmap_transform(self) -> np.ndarray | None:
        """

        get or set the cmap_transform across the collection

        With a single ``cmap`` the transform is 1D, one value per graphic, selecting each graphic's
        color. With an iterable of colormaps the transform is per-graphic, coloring each graphic
        along its datapoints.

        """

    @cmap_transform.setter
    def cmap_transform(self, value): ...
    @property
    def cmap_range(self) -> tuple[float, float] | None:
        """
        get or set the cmap_range of the graphics in the collection
        """

    @cmap_range.setter
    def cmap_range(self, value): ...
    def add_linear_selector(
        self, selection: float = None, padding: float = 0.0, axis: str = "x", **kwargs
    ) -> LinearSelector:
        """

        Add a :class:`.LinearSelector`.

        Parameters
        ----------
        selection: float, optional
            initial position of the selector along ``axis``, computed from the data if not given

        padding: float, default 0.0
            extra padding along the orthogonal axis to make the selector easier to grab

        axis: str, default "x"
            axis the selector moves along

        **kwargs
            passed to :class:`.LinearSelector`

        Returns
        -------
        LinearSelector

        """

    def add_linear_region_selector(
        self,
        selection: tuple[float, float] = None,
        padding: float = 0.0,
        axis: str = "x",
        **kwargs
    ) -> LinearRegionSelector:
        """

        Add a :class:`.LinearRegionSelector`.

        Parameters
        ----------
        selection: (float, float), optional
            initial bounds of the region along ``axis``, computed from the data if not given

        padding: float, default 0.0
            extra padding along the orthogonal axis to make the selector easier to grab

        axis: str, default "x"
            axis the selector spans

        **kwargs
            passed to :class:`.LinearRegionSelector`

        Returns
        -------
        LinearRegionSelector

        """

    def add_rectangle_selector(
        self, selection: tuple[float, float, float, float] = None, **kwargs
    ) -> RectangleSelector:
        """

        Add a :class:`.RectangleSelector`.

        Parameters
        ----------
        selection: (float, float, float, float), optional
            initial (xmin, xmax, ymin, ymax), computed from the data if not given

        **kwargs
            passed to :class:`.RectangleSelector`

        Returns
        -------
        RectangleSelector

        """

    def add_polygon_selector(
        self, selection: list[tuple[float, float]] = None, **kwargs
    ) -> PolygonSelector:
        """

        Add a :class:`.PolygonSelector`.

        Parameters
        ----------
        selection: list of (float, float), optional
            initial polygon points; if not given, you draw the polygon by clicking

        **kwargs
            passed to :class:`.PolygonSelector`

        Returns
        -------
        PolygonSelector

        """

class LineCollection(PositionsCollection):
    def __init__(
        self,
        data: Any,
        thickness: float = 2.0,
        colors: ColorLike | MultiColorLike = "w",
        cmap: ColormapLike | None = None,
        cmap_transform: np.ndarray | Iterable[int | float] | None = None,
        cmap_range: tuple[float, float] | None = None,
        size_space: Literal["screen", "world", "model"] = "screen",
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
    ) -> None:
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

        cmap_transform: np.ndarray, optional
            1D array-like of numerical values, if provided, these values are used to map the colors from the cmap

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

        Notes
        -----
        ``cmap`` and ``cmap_transform`` apply across the collection. A single ``cmap`` gives each graphic
        one color spread across the colormap, selected by a 1D ``cmap_transform`` (one value per graphic).
        An iterable of colormaps gives each graphic its own colormap along its datapoints, with a
        per-graphic ``cmap_transform``.
        """

    @property
    def data(self) -> JaggedCollectionFeature:
        """
        Line data to plot. Can provide 1D, 2D, or a 3D data.
        | If passing a 1D array, it is used to set the y-values and the x-values are generated as an integer range
        from [0, data.size]
        | 2D data must be of shape [n_points, 2]. 3D data must be of shape [n_points, 3]
        """

    @data.setter
    def data(self, value: Any) -> None: ...
    @property
    def colors(self) -> CollectionColors:
        """
        specify colors as a single human-readable string, a single RGBA array,
        or a Sequence (array, tuple, or list) of strings or RGBA arrays
        """

    @colors.setter
    def colors(
        self, value: ColorLike | MultiColorLike | Iterable[ColorLike | MultiColorLike]
    ) -> None: ...
    @property
    def size_space(self) -> CollectionFeatureAccessor:
        """
        coordinate space in which the thickness is expressed ("screen", "world", "model")
        """

    @size_space.setter
    def size_space(
        self,
        value: (
            Literal["screen", "world", "model"]
            | Iterable[Literal["screen", "world", "model"]]
        ),
    ) -> None: ...
    @property
    def names(self) -> CollectionFeatureAccessor:
        """
        name this graphic to use it as a key to access from the plot
        """

    @names.setter
    def names(self, value: str | Iterable[str]) -> None: ...
    @property
    def offsets(self) -> JaggedCollectionFeature:
        """
        (x, y, z) vector to offset this graphic from the origin
        """

    @offsets.setter
    def offsets(
        self, value: np.ndarray | tuple[float] | Iterable[np.ndarray | tuple[float]]
    ) -> None: ...
    @property
    def rotations(self) -> JaggedCollectionFeature:
        """
        rotation quaternion
        """

    @rotations.setter
    def rotations(
        self, value: np.ndarray | tuple[float] | Iterable[np.ndarray | tuple[float]]
    ) -> None: ...
    @property
    def scales(self) -> JaggedCollectionFeature:
        """
        (x, y, z) scale factors
        """

    @scales.setter
    def scales(
        self, value: np.ndarray | tuple[float] | Iterable[np.ndarray | tuple[float]]
    ) -> None: ...
    @property
    def alphas(self) -> CollectionFeatureAccessor:
        """
        The global alpha value, i.e. opacity, of the graphic.
        """

    @alphas.setter
    def alphas(self, value: float | Iterable[float]) -> None: ...
    @property
    def alpha_modes(self) -> CollectionFeatureAccessor:
        """
        The alpha-mode, e.g. 'auto', 'blend', 'weighted_blend', 'solid', or 'dither'.
        """

    @alpha_modes.setter
    def alpha_modes(self, value: str | Iterable[str]) -> None: ...
    @property
    def visibles(self) -> CollectionFeatureAccessor:
        """
        Whether the graphic is visible.
        """

    @visibles.setter
    def visibles(self, value: bool | Iterable[bool]) -> None: ...
    @property
    def thickness(self) -> CollectionFeatureAccessor:
        """
        thickness of the line
        """

    @thickness.setter
    def thickness(self, value: float | Iterable[float]) -> None: ...
    @property
    def dash_pattern(self) -> CollectionFeatureAccessor:
        """
        The dash pattern. May be a matplotlib-style string, one of ``"-", "--", "-.", ":"``
        or ``"solid", "dashed", "dashdot", "dotted"``, or a sequence of floats describing the
        length of strokes and gaps. Ignored when ``thin`` is True.
        """

    @dash_pattern.setter
    def dash_pattern(
        self, value: str | tuple | list | Iterable[str | tuple | list]
    ) -> None: ...
    @property
    def metadatas(self) -> CollectionFeatureAccessor:
        """
        metadata attached to this Graphic, this is for the user to manage
        """

    @metadatas.setter
    def metadatas(self, value: Any) -> None: ...

class ScatterCollection(PositionsCollection):
    def __init__(
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
        point_rotations: float | np.ndarray | None = 0.0,
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
    ) -> None:
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

        point_rotations: float, array-like, or None, default 0.0
            The rotation of the scatter points in radians. The rotation mode is determined automatically from
            the value: pass ``None`` (default) for "curve" mode, where each point's rotation follows the curve
            of the data (in screen space); a single float for the same rotation on every point ("uniform"); or
            an array of rotation values for per-point rotations ("vertex"). Units are in radians.

        sizes: float, np.ndarray, or Sequence[float], default 5
            size(s) of the scatter points. Specify a single size to use the same size for all points, or a
            Sequence of sizes for per-point sizes.

        size_space: str, default "screen"
            coordinate space in which the size is expressed, one of ("screen", "world", "model")

        kwargs
            passed to :class:`.Graphic`

        Notes
        -----
        ``cmap`` and ``cmap_transform`` apply across the collection. A single ``cmap`` gives each graphic
        one color spread across the colormap, selected by a 1D ``cmap_transform`` (one value per graphic).
        An iterable of colormaps gives each graphic its own colormap along its datapoints, with a
        per-graphic ``cmap_transform``.
        """

    @property
    def data(self) -> JaggedCollectionFeature:
        """
        Scatter data to plot, Can provide 2D, or a 3D data. 2D data must be of shape [n_points, 2].
        3D data must be of shape [n_points, 3]
        """

    @data.setter
    def data(self, value: Any) -> None: ...
    @property
    def colors(self) -> CollectionColors:
        """
        specify colors as a single human-readable string, a single RGBA array,
        or a Sequence (array, tuple, or list) of strings or RGBA arrays
        """

    @colors.setter
    def colors(
        self, value: ColorLike | MultiColorLike | Iterable[ColorLike | MultiColorLike]
    ) -> None: ...
    @property
    def size_space(self) -> CollectionFeatureAccessor:
        """
        coordinate space in which the size is expressed, one of ("screen", "world", "model")
        """

    @size_space.setter
    def size_space(self, value: str | Iterable[str]) -> None: ...
    @property
    def names(self) -> CollectionFeatureAccessor:
        """
        name this graphic to use it as a key to access from the plot
        """

    @names.setter
    def names(self, value: str | Iterable[str]) -> None: ...
    @property
    def offsets(self) -> JaggedCollectionFeature:
        """
        (x, y, z) vector to offset this graphic from the origin
        """

    @offsets.setter
    def offsets(
        self, value: np.ndarray | tuple[float] | Iterable[np.ndarray | tuple[float]]
    ) -> None: ...
    @property
    def rotations(self) -> JaggedCollectionFeature:
        """
        rotation quaternion
        """

    @rotations.setter
    def rotations(
        self, value: np.ndarray | tuple[float] | Iterable[np.ndarray | tuple[float]]
    ) -> None: ...
    @property
    def scales(self) -> JaggedCollectionFeature:
        """
        (x, y, z) scale factors
        """

    @scales.setter
    def scales(
        self, value: np.ndarray | tuple[float] | Iterable[np.ndarray | tuple[float]]
    ) -> None: ...
    @property
    def alphas(self) -> CollectionFeatureAccessor:
        """
        The global alpha value, i.e. opacity, of the graphic.
        """

    @alphas.setter
    def alphas(self, value: float | Iterable[float]) -> None: ...
    @property
    def alpha_modes(self) -> CollectionFeatureAccessor:
        """
        The alpha-mode, e.g. 'auto', 'blend', 'weighted_blend', 'solid', or 'dither'.
        """

    @alpha_modes.setter
    def alpha_modes(self, value: str | Iterable[str]) -> None: ...
    @property
    def visibles(self) -> CollectionFeatureAccessor:
        """
        Whether the graphic is visible.
        """

    @visibles.setter
    def visibles(self, value: bool | Iterable[bool]) -> None: ...
    @property
    def sizes(self) -> JaggedCollectionFeature:
        """
        size(s) of the scatter points. Specify a single size to use the same size for all points, or a
        Sequence of sizes for per-point sizes.
        """

    @sizes.setter
    def sizes(
        self,
        value: (
            float
            | np.ndarray
            | Sequence[float]
            | Iterable[float | np.ndarray | Sequence[float]]
        ),
    ) -> None: ...
    @property
    def markers(self) -> JaggedCollectionFeature:
        """
        The shape of the markers when `mode` is "markers". Specify a single marker to use the same
        marker for all points, or a Sequence of markers for per-vertex markers.
        """

    @markers.setter
    def markers(
        self,
        value: (
            str
            | np.ndarray
            | Sequence[str]
            | Iterable[str | np.ndarray | Sequence[str]]
        ),
    ) -> None: ...
    @property
    def edge_colors(self) -> CollectionColors:
        """
        edge color(s) of the markers, used when `mode` is "markers". Specify a single color to use the
        same edge color for all markers, or a Sequence of colors for per-vertex edge colors. Pass
        ``None`` for no edge color.
        """

    @edge_colors.setter
    def edge_colors(
        self,
        value: (
            ColorLike
            | MultiColorLike
            | None
            | Iterable[ColorLike | MultiColorLike | None]
        ),
    ) -> None: ...
    @property
    def edge_width(self) -> CollectionFeatureAccessor:
        """
        Width of the marker edges. used when `mode` is "markers".
        """

    @edge_width.setter
    def edge_width(self, value: float | Iterable[float]) -> None: ...
    @property
    def image(self) -> JaggedCollectionFeature:
        """
        renders an image at the scatter points, also known as sprites.
        The image color is multiplied with the point's "normal" color.
        """

    @image.setter
    def image(self, value: np.ndarray | Iterable[np.ndarray]) -> None: ...
    @property
    def point_rotations(self) -> JaggedCollectionFeature:
        """
        The rotation of the scatter points in radians. The rotation mode is determined automatically from
        the value: pass ``None`` (default) for "curve" mode, where each point's rotation follows the curve
        of the data (in screen space); a single float for the same rotation on every point ("uniform"); or
        an array of rotation values for per-point rotations ("vertex"). Units are in radians.
        """

    @point_rotations.setter
    def point_rotations(
        self, value: float | np.ndarray | None | Iterable[float | np.ndarray | None]
    ) -> None: ...
    @property
    def metadatas(self) -> CollectionFeatureAccessor:
        """
        metadata attached to this Graphic, this is for the user to manage
        """

    @metadatas.setter
    def metadatas(self, value: Any) -> None: ...

class ImageCollection(GraphicCollection):
    def __init__(
        self,
        data: Any,
        vmin: float = None,
        vmax: float = None,
        cmap: str = "plasma",
        gamma: float = 1.0,
        interpolation: Literal["nearest", "linear"] = "nearest",
        cmap_interpolation: Literal["nearest", "linear"] = "linear",
        colorspace: ColorspacesRGB = "srgb",
        cpu_buffer: bool = True,
        texture_usage: wgpu.TextureUsage = 0,
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
    ) -> None:
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

        texture_usage: wgpu.TextureUsage, default 0
            Extra wgpu texture usage flags. Usage cannot be changed after the texture is created

        kwargs:
            additional keyword arguments passed to :class:`.Graphic`


        """

    @property
    def data(self) -> JaggedCollectionFeature:
        """
        array-like, usually numpy.ndarray, must support ``memoryview()``
        | shape must be ``[n_rows, n_cols]``, ``[n_rows, n_cols, 3]`` for RGB or ``[n_rows, n_cols, 4]`` for RGBA
        """

    @data.setter
    def data(self, value: Any) -> None: ...
    @property
    def cmap(self) -> CollectionFeatureAccessor:
        """
        colormap to use to display the data. For supported colormaps see the
        ``cmap`` library catalogue: https://cmap-docs.readthedocs.io/en/stable/catalog/
        """

    @cmap.setter
    def cmap(self, value: str | Iterable[str]) -> None: ...
    @property
    def gamma(self) -> CollectionFeatureAccessor:
        """
        gamma correction, the value scaled by ``vmin`` and ``vmax`` is raised to the power of ``gamma``
        """

    @gamma.setter
    def gamma(self, value: float | Iterable[float]) -> None: ...
    @property
    def vmin(self) -> CollectionFeatureAccessor:
        """
        minimum value for color scaling, estimated from data if not provided
        """

    @vmin.setter
    def vmin(self, value: float | Iterable[float]) -> None: ...
    @property
    def vmax(self) -> CollectionFeatureAccessor:
        """
        maximum value for color scaling, estimated from data if not provided
        """

    @vmax.setter
    def vmax(self, value: float | Iterable[float]) -> None: ...
    @property
    def interpolation(self) -> CollectionFeatureAccessor:
        """
        interpolation filter, one of "nearest" or "linear"
        """

    @interpolation.setter
    def interpolation(
        self,
        value: Literal["nearest", "linear"] | Iterable[Literal["nearest", "linear"]],
    ) -> None: ...
    @property
    def cmap_interpolation(self) -> CollectionFeatureAccessor:
        """
        colormap interpolation method, one of "nearest" or "linear"
        """

    @cmap_interpolation.setter
    def cmap_interpolation(
        self,
        value: Literal["nearest", "linear"] | Iterable[Literal["nearest", "linear"]],
    ) -> None: ...
    @property
    def names(self) -> CollectionFeatureAccessor:
        """
        name this graphic to use it as a key to access from the plot
        """

    @names.setter
    def names(self, value: str | Iterable[str]) -> None: ...
    @property
    def offsets(self) -> JaggedCollectionFeature:
        """
        (x, y, z) vector to offset this graphic from the origin
        """

    @offsets.setter
    def offsets(
        self, value: np.ndarray | tuple[float] | Iterable[np.ndarray | tuple[float]]
    ) -> None: ...
    @property
    def rotations(self) -> JaggedCollectionFeature:
        """
        rotation quaternion
        """

    @rotations.setter
    def rotations(
        self, value: np.ndarray | tuple[float] | Iterable[np.ndarray | tuple[float]]
    ) -> None: ...
    @property
    def scales(self) -> JaggedCollectionFeature:
        """
        (x, y, z) scale factors
        """

    @scales.setter
    def scales(
        self, value: np.ndarray | tuple[float] | Iterable[np.ndarray | tuple[float]]
    ) -> None: ...
    @property
    def alphas(self) -> CollectionFeatureAccessor:
        """
        The global alpha value, i.e. opacity, of the graphic.
        """

    @alphas.setter
    def alphas(self, value: float | Iterable[float]) -> None: ...
    @property
    def alpha_modes(self) -> CollectionFeatureAccessor:
        """
        The alpha-mode, e.g. 'auto', 'blend', 'weighted_blend', 'solid', or 'dither'.
        """

    @alpha_modes.setter
    def alpha_modes(self, value: str | Iterable[str]) -> None: ...
    @property
    def visibles(self) -> CollectionFeatureAccessor:
        """
        Whether the graphic is visible.
        """

    @visibles.setter
    def visibles(self, value: bool | Iterable[bool]) -> None: ...
    @property
    def metadatas(self) -> CollectionFeatureAccessor:
        """
        metadata attached to this Graphic, this is for the user to manage
        """

    @metadatas.setter
    def metadatas(self, value: Any) -> None: ...

class ImageGrid(ImageCollection):
    def __init__(
        self,
        data: Any,
        vmin: float = None,
        vmax: float = None,
        cmap: str = "plasma",
        gamma: float = 1.0,
        interpolation: Literal["nearest", "linear"] = "nearest",
        cmap_interpolation: Literal["nearest", "linear"] = "linear",
        colorspace: ColorspacesRGB = "srgb",
        cpu_buffer: bool = True,
        texture_usage: wgpu.TextureUsage = 0,
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
    ) -> None:
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

        texture_usage: wgpu.TextureUsage, default 0
            Extra wgpu texture usage flags. Usage cannot be changed after the texture is created

        kwargs:
            additional keyword arguments passed to :class:`.Graphic`


        """

class GraphicStack:
    @property
    def separation(self) -> np.ndarray:
        """
        get or set the (x, y, z) gap added to the step along the stacking axes
        """

    @separation.setter
    def separation(self, value: tuple[float, float, float]): ...
    @property
    def steps(self) -> np.ndarray | None:
        """
        get or set the per-graphic (x, y, z) steps used to space the stack, ``None`` to auto-determine
        """

    @steps.setter
    def steps(self, value: np.ndarray | None): ...
    @property
    def separation_axis(self) -> str:
        """
        get or set the axes to stack along, e.g. "y", "xy", "xyz"
        """

    @separation_axis.setter
    def separation_axis(self, value: str): ...

class LineStack(GraphicStack, LineCollection):
    def __init__(
        self,
        data: Any,
        thickness: float = 2.0,
        colors: ColorLike | MultiColorLike = "w",
        cmap: ColormapLike | None = None,
        cmap_transform: np.ndarray | Iterable[int | float] | None = None,
        cmap_range: tuple[float, float] | None = None,
        size_space: Literal["screen", "world", "model"] = "screen",
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
    ) -> None:
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

        cmap_transform: np.ndarray, optional
            1D array-like of numerical values, if provided, these values are used to map the colors from the cmap

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

        Notes
        -----
        ``cmap`` and ``cmap_transform`` apply across the collection. A single ``cmap`` gives each graphic
        one color spread across the colormap, selected by a 1D ``cmap_transform`` (one value per graphic).
        An iterable of colormaps gives each graphic its own colormap along its datapoints, with a
        per-graphic ``cmap_transform``.
        """

class ScatterStack(GraphicStack, ScatterCollection):
    def __init__(
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
        point_rotations: float | np.ndarray | None = 0.0,
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
    ) -> None:
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

        point_rotations: float, array-like, or None, default 0.0
            The rotation of the scatter points in radians. The rotation mode is determined automatically from
            the value: pass ``None`` (default) for "curve" mode, where each point's rotation follows the curve
            of the data (in screen space); a single float for the same rotation on every point ("uniform"); or
            an array of rotation values for per-point rotations ("vertex"). Units are in radians.

        sizes: float, np.ndarray, or Sequence[float], default 5
            size(s) of the scatter points. Specify a single size to use the same size for all points, or a
            Sequence of sizes for per-point sizes.

        size_space: str, default "screen"
            coordinate space in which the size is expressed, one of ("screen", "world", "model")

        kwargs
            passed to :class:`.Graphic`

        Notes
        -----
        ``cmap`` and ``cmap_transform`` apply across the collection. A single ``cmap`` gives each graphic
        one color spread across the colormap, selected by a 1D ``cmap_transform`` (one value per graphic).
        An iterable of colormaps gives each graphic its own colormap along its datapoints, with a
        per-graphic ``cmap_transform``.
        """
