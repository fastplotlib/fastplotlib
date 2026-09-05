import warnings
from collections.abc import Callable
from typing import Any, Literal, Sequence, Hashable

import numpy as np
from numpy.typing import ArrayLike

from ... import (
    ScatterCollection,
    ScatterStack,
    LineCollection,
    LineStack,
    ImageGraphic,
)
from ...layouts import Subplot
from ...utils import ArrayProtocol, enums
from . import NDImageProcessor, NDImage, NDPositions, NDTimeseries, NDVectors
from ._nd_positions._nd_positions import (
    NDPositionsProcessor,
    ColorsType,
    FeatureCallable,
    MarkersType,
    SizesType,
)
from ._index import AutoRangeContinuous
from ._video import VideoProcessor
from ._base import NDGraphic, WindowFuncCallable


class NDWSubplot:
    """
    Entry point for adding ``NDGraphic`` objects to a subplot of an ``NDWidget``.

    Accessed via ``ndw[row, col]`` or ``ndw["subplot_name"]``.
    Each ``add_nd_<...>`` method constructs the appropriate ``NDGraphic``, registers it with the parent
    ``ReferenceIndex``, appends it to this subplot and returns the ``NDGraphic`` instance to the user.

    Note: ``NDWSubplot`` is not meant to be constructed directly, it only exists as part of an ``NDWidget``
    """

    def __init__(self, ndw, subplot: Subplot):
        self.ndw = ndw
        self._subplot = subplot

        self._nd_graphics = list()

    @property
    def subplot(self) -> Subplot:
        """The ``Subplot`` of the ``NDWidget`` figure that this ``NDWSubplot`` adds graphics to"""
        return self._subplot

    @property
    def nd_graphics(self) -> tuple[NDGraphic]:
        """all the NDGraphic instance in this subplot"""
        return tuple(self._nd_graphics)

    def __getitem__(self, key) -> NDGraphic:
        # get a specific NDGraphic by index or name
        if isinstance(key, (int, np.integer)):
            return self.nd_graphics[key]

        for g in self.nd_graphics:
            if g.name == key:
                return g

        else:
            raise KeyError(f"NDGraphc with given key not found: {key}")

    def delete_nd_graphic(self, ndg: NDGraphic):
        """Delete an NDGraphic from the subplot"""

        # TODO: verify that this actually garbage collects
        del ndg.data
        self.subplot.delete_graphic(ndg.graphic)
        self._nd_graphics.remove(ndg)

        del ndg

    def _check_slider_dims(
        self,
        dims: Sequence[Hashable],
        spatial_dims: Sequence[Hashable],
        data: ArrayProtocol | None,
        positions: bool = False,
    ):
        """
        Make sure every slider (non-spatial) dim of a graphic being added has a
        reference range. A dim without one gets an ``AutoRangeContinuous`` sized to
        the data, an existing ``AutoRangeContinuous`` is grown to fit, and an
        explicit range is left untouched.
        """
        if data is None:
            # size is unknown, an explicit range is still required
            return

        dims = tuple(dims)
        slider_dims = set(dims) - set(spatial_dims)
        if positions:
            # the datapoints `p` axis is a spatial dim that also needs a reference range
            slider_dims.add(spatial_dims[1])

        for dim in slider_dims:
            size = data.shape[dims.index(dim)]

            if dim not in self.ndw.indices.dims:
                warnings.warn(
                    f"No reference range specified for non-spatial dim '{dim}', "
                    f"auto-generating an `AutoRangeContinuous(0, {size}, 1)`."
                )
                self.ndw.indices.push_dims({dim: AutoRangeContinuous(0, size, 1)})

            elif isinstance(self.ndw.indices.ref_ranges[dim], AutoRangeContinuous):
                # grow the existing auto range to fit this array
                self.ndw.indices.ref_ranges[dim].stop = max(
                    self.ndw.indices.ref_ranges[dim].stop, size
                )

    def add_nd_image(
        self,
        data: ArrayProtocol | None,
        dims: Sequence[str],
        spatial_dims: (
            tuple[str, str] | tuple[str, str, str]
        ),  # must be in order! [rows, cols] | [z, rows, cols]
        rgb_dim: str | None = None,
        window_funcs: dict[
            str, tuple[WindowFuncCallable | None, int | float | None]
        ] = None,
        window_order: tuple[str, ...] = None,
        spatial_func: Callable[[ArrayProtocol], ArrayProtocol] = None,
        compute_histogram: bool = True,
        slider_dim_transforms: dict[str, Callable[[Any], int] | ArrayLike] = None,
        processor_type: type[NDImageProcessor] = NDImageProcessor,
        colorspace: Literal[
            "srgb", "tex-srgb", "physical", "yuv420p", "yuv444p"
        ] = "srgb",
        colorrange: Literal["full", "limited"] = "full",
        name: str = None,
        graphic_kwargs: dict = None,
    ) -> NDImage:
        """
        Add an n-dimensional image or volume to this subplot.

        Every dim that is not listed in ``spatial_dims`` becomes a slider dim.

        Parameters
        ----------
        data: ArrayProtocol or None
            n-dimensional image data, must have 2 or more dims. Pass ``None`` to create the ``NDImage`` without a
            graphic and set the data later using ``nd_image.data``, the slider dims then require an explicit
            reference range in the ``NDWidget``.

        dims: Sequence[str]
            name for every dim of ``data``, in order. They do not need to be in display order, ex: an array whose
            dims are ``("col", "depth", "row", "time")`` with ``spatial_dims`` of ``("row", "col")``.

        spatial_dims: tuple[str, str] | tuple[str, str, str]
            The 2 or 3 spatial dims **in display order**, which also determines the graphic used for rendering:

            * ``(rows, cols)``, a 2D grayscale ``ImageGraphic``
            * ``(rows, cols, rgb_dim)``, a 2D RGB(A) ``ImageGraphic``
            * ``(z, rows, cols)``, a 3D ``ImageVolumeGraphic``

        rgb_dim: str, optional
            Name of the RGB(A) dim, if present. It must be listed in ``spatial_dims`` and be of size 3 or 4.

        window_funcs: dict[str, tuple[WindowFuncCallable | None, int | float | None]], optional
            Per-slider-dim window functions applied around the current slider position, ex:
            ``{"time": (np.mean, 2.5)}``. Each value is a ``(func, window_size)`` pair where:

            * *func* must accept ``axis: int`` and ``keepdims: bool`` kwargs (ex: ``np.mean``, ``np.max``). It
              **must** return an array that has the same dims as the input, therefore the size of any dim along
              which it was applied should reduce to ``1``. These dims must not be removed by the window func.

            * *window_size* is in reference-space units (ex: 2.5 seconds).

        window_order: tuple[str, ...], optional
            Order in which the window functions are applied across dims. Only dims listed here have their window
            function applied, ``window_funcs`` are ignored for any dim not specified in ``window_order``.

        spatial_func: Callable[[ArrayProtocol], ArrayProtocol], optional
            A function applied to the spatial slice *after* the window funcs, right before rendering.

        compute_histogram: bool, default ``True``
            Estimate a histogram of the data and display an ``ImguiColorbar`` on the right edge of the subplot,
            which is used to interactively set vmin, vmax. Disable if random access of the data is not
            blazing-fast (ex: data that uses video codecs), or if a histogram is not useful for this data.

        slider_dim_transforms: dict mapping dim_name -> Callable, an ArrayLike, or None, optional
            Per-slider-dim mapping from reference-space values to local array indices. An array of reference
            values may be given instead of a callable, ``searchsorted`` is then used as the transform (ex: a
            timestamps array). Any dim without a transform uses the identity mapping, i.e. the current reference
            value is rounded to the nearest integer and used as the array index.

        processor_type: type[NDImageProcessor], default ``NDImageProcessor``
            ``NDImageProcessor`` subclass that manages the data and produces the data slices.

        colorspace: "srgb" | "tex-srgb" | "physical" | "yuv420p" | "yuv444p", default "srgb"
            Colorspace in which to interpret the data. The RGB colorspaces are rendered using an ``ImageGraphic``
            or ``ImageVolumeGraphic``, see :class:`.ImageGraphic` for their meaning. The YUV colorspaces are
            rendered using an ``ImageYUVGraphic``, see :class:`.ImageYUVGraphic`.

        colorrange: "full" | "limited", default "full"
            Used only for the YUV colorspaces, see :class:`.ImageYUVGraphic`.

        name: str, optional
            Name for this ``NDGraphic``, used to retrieve it with ``nd_subplot[name]``.

        graphic_kwargs: dict, optional
            passed to the underlying image graphic, ex: ``{"cmap": "viridis", "interpolation": "linear"}``

        Returns
        -------
        NDImage

        """
        self._check_slider_dims(dims, spatial_dims, data)

        nd = NDImage(
            self.ndw.indices,
            nd_subplot=self,
            data=data,
            dims=dims,
            spatial_dims=spatial_dims,
            rgb_dim=rgb_dim,
            window_funcs=window_funcs,
            window_order=window_order,
            spatial_func=spatial_func,
            compute_histogram=compute_histogram,
            slider_dim_transforms=slider_dim_transforms,
            processor_type=processor_type,
            colorspace=colorspace,
            colorrange=colorrange,
            name=name,
            graphic_kwargs=graphic_kwargs,
        )

        self._nd_graphics.append(nd)
        return nd

    def add_video(
            self,
            data: ArrayProtocol | None,
            dims: Sequence[str],
            spatial_dims: tuple[str, str] | tuple[str, str, str],
            rgb_dim: str | None = None,
            colorspace: enums.ColorspacesYUV | enums.ColorspacesRGB = "yuv420p",
            colorrange: enums.ColorRange = "limited",
            processor_type: NDImageProcessor = VideoProcessor,
            window_funcs: dict[
                str, tuple[WindowFuncCallable | None, int | float | None]
            ] = None,
            window_order: tuple[str, ...] = None,
            spatial_func: Callable[[ArrayProtocol], ArrayProtocol] = None,
            compute_histogram: bool = True,
            slider_dim_transforms: dict[str, Callable[[Any], int] | ArrayLike] = None,
            name: str = None,
            graphic_kwargs: dict = None,
    ) -> NDImage:
        """
        Add a video to this subplot.

        This is usually what you want for video data. Videos are usually stored in a YUV colorspace, and sending
        the YUV planes to the GPU is much faster than converting each frame to RGB and copying it into an sRGB
        texture.

        We strongly recommend using ``asyncvideo`` for the ``data`` object, it is the most efficient async video
        reader that we know of for visualization purposes: https://pypi.org/project/asyncvideo/

        Same as :meth:`add_nd_image` but uses a :class:`VideoProcessor` and YUV defaults. The ``VideoProcessor``
        reads the frame at the current index directly, it does not apply ``window_funcs``.

        Parameters
        ----------
        data: ArrayProtocol or None
            video data, an object that decodes frames on demand, ex: an ``asyncvideo`` reader. Pass ``None`` to
            create the ``NDImage`` without a graphic and set the data later using ``nd_image.data``, the slider
            dims then require an explicit reference range in the ``NDWidget``.

        dims: Sequence[str]
            name for every dim of ``data``, in order. They do not need to be in display order.

        spatial_dims: tuple[str, str] | tuple[str, str, str]
            The 2 or 3 spatial dims **in display order**, see :meth:`add_nd_image`.

        rgb_dim: str, optional
            Name of the RGB(A) dim, if present. It must be listed in ``spatial_dims`` and be of size 3 or 4.

        colorspace: "yuv420p" | "yuv444p" | "srgb" | "tex-srgb" | "physical", default "yuv420p"
            Colorspace in which to interpret the data. The YUV colorspaces are rendered using an
            ``ImageYUVGraphic``, see :class:`.ImageYUVGraphic`. The RGB colorspaces are rendered using an
            ``ImageGraphic`` or ``ImageVolumeGraphic``, see :class:`.ImageGraphic`.

        colorrange: "full" | "limited", default "limited"
            Used only for the YUV colorspaces, see :class:`.ImageYUVGraphic`. Most videos use "limited".

        processor_type: type[NDImageProcessor], default ``VideoProcessor``
            ``NDImageProcessor`` subclass that manages the data and produces the data slices.

        window_funcs: dict[str, tuple[WindowFuncCallable | None, int | float | None]], optional
            Per-slider-dim window functions, see :meth:`add_nd_image`. Ignored by the default
            ``VideoProcessor``.

        window_order: tuple[str, ...], optional
            Order in which the window functions are applied across dims. Ignored by the default
            ``VideoProcessor``.

        spatial_func: Callable[[ArrayProtocol], ArrayProtocol], optional
            A function applied to the spatial slice right before rendering.

        compute_histogram: bool, default ``True``
            Estimate a histogram of the data and display an ``ImguiColorbar`` on the right edge of the subplot,
            which is used to interactively set vmin, vmax. Usually disabled for video since it requires random
            access of frames, which is slow for data that uses video codecs.

        slider_dim_transforms: dict mapping dim_name -> Callable, an ArrayLike, or None, optional
            Per-slider-dim mapping from reference-space values to local array indices, ex: an array of frame
            timestamps to map seconds onto frame indices. See :meth:`add_nd_image`.

        name: str, optional
            Name for this ``NDGraphic``, used to retrieve it with ``nd_subplot[name]``.

        graphic_kwargs: dict, optional
            passed to the underlying image graphic

        Returns
        -------
        NDImage

        """
        return self.add_nd_image(
            data=data,
            dims=dims,
            spatial_dims=spatial_dims,
            rgb_dim=rgb_dim,
            colorspace=colorspace,
            colorrange=colorrange,
            processor_type=processor_type,
            window_funcs=window_funcs,
            window_order=window_order,
            spatial_func=spatial_func,
            compute_histogram=compute_histogram,
            slider_dim_transforms=slider_dim_transforms,
            name=name,
            graphic_kwargs=graphic_kwargs,
        )

    def add_nd_vectors(
        self,
        data: ArrayProtocol | None,
        dims: Sequence[str],
        spatial_dims: tuple[str, str, str],
        window_funcs: dict[
            str, tuple[WindowFuncCallable | None, int | float | None]
        ] = None,
        window_order: tuple[str, ...] = None,
        spatial_func: Callable[[ArrayProtocol], ArrayProtocol] = None,
        slider_dim_transforms: dict[str, Callable[[Any], int] | ArrayLike] = None,
        name: str = None,
        graphic_kwargs: dict = None,
    ) -> NDVectors:
        """
        Add n-dimensional vectors to this subplot, similar to matplotlib quiver.

        Every dim that is not listed in ``spatial_dims`` becomes a slider dim.

        Parameters
        ----------
        data: ArrayProtocol or None
            n-dimensional vector data of shape ``[..., n_vectors, 2, 2]`` or ``[..., n_vectors, 2, 3]``, where
            ``data[..., 0, :]`` are the vector positions and ``data[..., 1, :]`` are the vector directions. Pass
            ``None`` to create the ``NDVectors`` without a graphic and set the data later using
            ``nd_vectors.data``, the slider dims then require an explicit reference range in the ``NDWidget``.

        dims: Sequence[str]
            name for every dim of ``data``, in order. They do not need to be in display order.

        spatial_dims: tuple[str, str, str]
            The 3 spatial dims **in order**: ``(n_vectors, positions_and_directions, xy(z))``. The
            positions/directions dim must be of size 2 and the coordinate dim of size 2 or 3.

        window_funcs: dict[str, tuple[WindowFuncCallable | None, int | float | None]], optional
            Per-slider-dim window functions applied around the current slider position, ex:
            ``{"time": (np.mean, 2.5)}``. Each value is a ``(func, window_size)`` pair where:

            * *func* must accept ``axis: int`` and ``keepdims: bool`` kwargs (ex: ``np.mean``, ``np.max``). It
              **must** return an array that has the same dims as the input, therefore the size of any dim along
              which it was applied should reduce to ``1``. These dims must not be removed by the window func.

            * *window_size* is in reference-space units (ex: 2.5 seconds).

        window_order: tuple[str, ...], optional
            Order in which the window functions are applied across dims. Only dims listed here have their window
            function applied, ``window_funcs`` are ignored for any dim not specified in ``window_order``.

        spatial_func: Callable[[ArrayProtocol], ArrayProtocol], optional
            A function applied to the spatial slice *after* the window funcs, right before rendering.

        slider_dim_transforms: dict mapping dim_name -> Callable, an ArrayLike, or None, optional
            Per-slider-dim mapping from reference-space values to local array indices. An array of reference
            values may be given instead of a callable, ``searchsorted`` is then used as the transform (ex: a
            timestamps array). Any dim without a transform uses the identity mapping, i.e. the current reference
            value is rounded to the nearest integer and used as the array index.

        name: str, optional
            Name for this ``NDGraphic``, used to retrieve it with ``nd_subplot[name]``.

        graphic_kwargs: dict, optional
            passed to the underlying :class:`.VectorsGraphic`, ex: ``{"color": "cyan", "size": 0.5}``

        Returns
        -------
        NDVectors

        """
        self._check_slider_dims(dims, spatial_dims, data)

        nd = NDVectors(
            self.ndw.indices,
            nd_subplot=self,
            data=data,
            dims=dims,
            spatial_dims=spatial_dims,
            window_funcs=window_funcs,
            window_order=window_order,
            spatial_func=spatial_func,
            slider_dim_transforms=slider_dim_transforms,
            name=name,
            graphic_kwargs=graphic_kwargs,
        )

        self._nd_graphics.append(nd)
        return nd

    def add_nd_scatter(
        self,
        data: ArrayProtocol | None,
        dims: Sequence[str],
        spatial_dims: tuple[str, str, str],
        *args,
        processor: type[NDPositionsProcessor] = NDPositionsProcessor,
        display_window: int | float | None = 10,
        window_funcs: dict[
            str, tuple[WindowFuncCallable | None, int | float | None]
        ] = None,
        window_order: tuple[str, ...] = None,
        spatial_func: Callable[[ArrayProtocol], ArrayProtocol] = None,
        slider_dim_transforms: dict[str, Callable[[Any], int] | ArrayLike] = None,
        max_display_datapoints: int = 1_000,
        datapoints_window_func: tuple[Callable, str, int | float] | None = None,
        colors: ColorsType = None,
        cmap: str | Sequence[str] = None,
        cmap_transform: np.ndarray | FeatureCallable = None,
        cmap_range: tuple[float, float] = None,
        sizes: SizesType = None,
        markers: MarkersType = None,
        name: str = None,
        graphic_kwargs: dict = None,
        processor_kwargs: dict = None,
    ) -> NDPositions:
        """
        Add n-dimensional positional data to this subplot, rendered as a ``ScatterCollection``.

        Every dim that is not listed in ``spatial_dims`` becomes a slider dim. The datapoints dim, ``p``, is both
        a spatial dim and a slider dim, it is windowed by ``display_window`` and ``datapoints_window_func``
        rather than by ``window_funcs``.

        Parameters
        ----------
        data: ArrayProtocol or None
            n-dimensional positional data.

            Ex: an array of shape ``[n_trials, n_scatters, n_points, 2]`` with ``dims`` of
            ``("trial", "scatter", "point", "xy")`` and ``spatial_dims`` of ``("scatter", "point", "xy")``.

            Pass ``None`` to create the ``NDPositions`` without a graphic and set the data later using
            ``nd_positions.data``, the slider dims then require an explicit reference range in the ``NDWidget``.

        dims: Sequence[str]
            name for every dim of ``data``, in order.

        spatial_dims: tuple[str, str, str]
            The 3 spatial dims **in display order**: ``(n_graphics, p, <value dim>)``, i.e. the number of
            scatters in the collection, the number of datapoints ``p`` in each of them, and the value dim which
            holds the xy or xyz coordinate and must be of size 2 or 3. The dims do not need to be in this order
            in the array, the data slice is transposed into display order.

        args
            extra positional arguments passed to the ``processor`` constructor.

        processor: type[NDPositionsProcessor], default ``NDPositionsProcessor``
            ``NDPositionsProcessor`` subclass that manages the data and produces the data slices.

        display_window: int, float or None, default 10
            Size of the window of the ``p`` dim to render, in the reference units of that dim, centered on its
            current index. Use ``None`` to render every datapoint, or ``0`` to render only the datapoint at the
            current index. This is what makes out-of-core rendering possible, i.e. rendering a window of a
            dataset that is larger than GPU VRAM.

        window_funcs: dict[str, tuple[WindowFuncCallable | None, int | float | None]], optional
            Per-slider-dim window functions applied around the current slider position, ex:
            ``{"trial": (np.mean, 5)}``. Each value is a ``(func, window_size)`` pair where:

            * *func* must accept ``axis: int`` and ``keepdims: bool`` kwargs (ex: ``np.mean``, ``np.max``). It
              **must** return an array that has the same dims as the input, therefore the size of any dim along
              which it was applied should reduce to ``1``. These dims must not be removed by the window func.

            * *window_size* is in reference-space units.

            Not used for the ``p`` dim, see ``datapoints_window_func``.

        window_order: tuple[str, ...], optional
            Order in which the window functions are applied across dims. Only dims listed here have their window
            function applied, ``window_funcs`` are ignored for any dim not specified in ``window_order``.

        spatial_func: Callable[[ArrayProtocol], ArrayProtocol], optional
            A function applied to the spatial slice *after* the window funcs, right before rendering.

        slider_dim_transforms: dict[str, Callable[[Any], int] | ArrayLike], optional
            Per-slider-dim mapping from reference-space values to local array indices. An array of reference
            values may be given instead of a Callable, ``searchsorted`` is then used as the transform (ex: a
            timestamps array). Any dim without a transform uses the identity mapping, i.e. the current reference
            value is rounded to the nearest integer and used as the array index.

        max_display_datapoints: int, default 1_000
            Maximum number of datapoints to render per graphic. The step size of the display window slice is set
            from this using floor division.

        datapoints_window_func: tuple[Callable, str, int | float], optional
            Window function applied along the ``p`` dim after the display window has been taken, as
            ``(func, apply_dims, window_size)`` where:

            * *func* must accept an ``axis: int`` kwarg (ex: ``np.mean``, ``np.max``). It is given a sliding
              window view of the data and is reduced along the window axis.

            * *apply_dims* names the coordinates of the value dim to apply it to, one of ``"all", "x", "y",
              "z", "xy", "xz", "yz", "xyz"``. Coordinates that are not named are passed through unchanged.

            * *window_size* is in the reference units of the ``p`` dim. It is mapped to array indices, clamped to
              a minimum of 3, and rounded up to an odd size.

            If used, ``display_window`` is approximate and not exact due to padding from the window size.

        colors: str | Sequence[str] | np.ndarray | FeatureCallable, optional
            Colors of the scatters. Mutually exclusive with ``cmap``, setting one clears the other.

            * static, a single color for every graphic, ex: ``"cyan"`` or an RGBA sequence of 4 floats
            * static, one color per graphic, ``[n_graphics]`` of str or ``[n_graphics, 4]`` RGBA
            * windowed, one color per datapoint, ``[n_graphics, p, 4]`` RGBA
            * windowed, a ``FeatureCallable``

        cmap: str | Sequence[str], optional
            Colormap applied to the scatters, always static. A single name for every graphic, or an iterable of
            ``[n_graphics]`` names for a colormap per graphic. Mutually exclusive with ``colors``.

        cmap_transform: np.ndarray | FeatureCallable, optional
            Values that the colormap colors are mapped from.

            * static, one value per graphic, ``[n_graphics]``, so each graphic gets a single color
            * windowed, one value per datapoint, ``[n_graphics, p]``
            * windowed, a ``FeatureCallable``

        cmap_range: (float, float) | np.ndarray, optional
            The (min, max) of ``cmap_transform`` mapped onto the colormap, or ``[n_graphics, 2]`` for a range per
            graphic. A windowed array ``cmap_transform`` defaults to its own (min, max) over the full ``p`` dim,
            so the display window keeps its position within the colormap. A ``FeatureCallable`` transform
            requires an explicit range, its full range is not knowable without evaluating it everywhere.

        sizes: float | Sequence[float] | np.ndarray | FeatureCallable, optional
            Size of the scatter points.

            * static, a single size for every graphic, or ``[n_graphics]`` sizes for one size per graphic
            * windowed, one size per datapoint, ``[n_graphics, p]``
            * windowed, a ``FeatureCallable``

        markers: str | Sequence[str] | np.ndarray | FeatureCallable, optional
            Marker shape of the scatter points.

            * static, a single marker for every graphic, or ``[n_graphics]`` markers for one per graphic
            * windowed, one marker per datapoint, ``[n_graphics, p]``
            * windowed, a ``FeatureCallable``

        name: str, optional
            Name for this ``NDGraphic``, used to retrieve it with ``nd_subplot[name]``.

        graphic_kwargs: dict, optional
            passed to the underlying ``ScatterCollection``

        processor_kwargs: dict, optional
            passed to the ``processor`` constructor.

        Returns
        -------
        NDPositions

        Notes
        -----
        Each of the other graphic features is either *windowed* or *static*, decided from the value itself:

        * **windowed**: a ``FeatureCallable``, or an array whose axis 1 spans the ``p`` dim. It is re-sliced with
          the same display window slice as the data on every update, so the feature carries a value per
          displayed datapoint. An array **must** span the **full** ``p`` dim of the data, i.e.
          ``[n_graphics, p, <value dim>]``, since it is indexed with an index into the full ``p`` dim. A
          ``FeatureCallable`` is passed the data slice and that display window slice, and returns the feature
          values for the displayed datapoints.

        * **static**: anything else. It is set once on the collection, ex: a single value for every graphic,
          ``[n_graphics]`` values for one per graphic, or an iterator of per-graphic values such as
          ``itertools.cycle(["jet", "viridis"])``.

        """
        self._check_slider_dims(dims, spatial_dims, data, positions=True)

        nd = NDPositions(
            self.ndw.indices,
            self,
            data,
            dims,
            spatial_dims,
            *args,
            graphic_type=ScatterCollection,
            processor=processor,
            display_window=display_window,
            window_funcs=window_funcs,
            window_order=window_order,
            spatial_func=spatial_func,
            slider_dim_transforms=slider_dim_transforms,
            max_display_datapoints=max_display_datapoints,
            datapoints_window_func=datapoints_window_func,
            colors=colors,
            cmap=cmap,
            cmap_transform=cmap_transform,
            cmap_range=cmap_range,
            sizes=sizes,
            markers=markers,
            name=name,
            graphic_kwargs=graphic_kwargs,
            processor_kwargs=processor_kwargs,
        )

        self._nd_graphics.append(nd)
        return nd

    def add_nd_timeseries(
        self,
        data: ArrayProtocol | None,
        dims: Sequence[str],
        spatial_dims: tuple[str, str, str],
        *args,
        graphic_type: type[
            LineCollection | LineStack | ScatterCollection | ScatterStack | ImageGraphic
        ] = LineStack,
        x_range_mode: Literal["fixed", "auto"] | None = "auto",
        processor: type[NDPositionsProcessor] = NDPositionsProcessor,
        display_window: int | float | None = 10,
        window_funcs: dict[
            str, tuple[WindowFuncCallable | None, int | float | None]
        ] = None,
        window_order: tuple[str, ...] = None,
        spatial_func: Callable[[ArrayProtocol], ArrayProtocol] = None,
        slider_dim_transforms: dict[str, Callable[[Any], int] | ArrayLike] = None,
        max_display_datapoints: int = 1_000,
        datapoints_window_func: tuple[Callable, str, int | float] | None = None,
        colors: ColorsType = None,
        cmap: str | Sequence[str] = None,
        cmap_transform: np.ndarray | FeatureCallable = None,
        cmap_range: tuple[float, float] = None,
        thickness: float | Sequence[float] = None,
        sizes: SizesType = None,
        markers: MarkersType = None,
        name: str = None,
        graphic_kwargs: dict = None,
        processor_kwargs: dict = None,
    ) -> NDTimeseries:
        """
        Add n-dimensional timeseries data to this subplot, where the ``p`` dim is a time-like x-axis.

        Every dim that is not listed in ``spatial_dims`` becomes a slider dim. The datapoints dim, ``p``, is both
        a spatial dim and a slider dim, it is windowed by ``display_window`` and ``datapoints_window_func``
        rather than by ``window_funcs``.

        A ``LinearSelector`` that marks the current index of the ``p`` dim is added to the subplot. Dragging it
        sets that index in the ``ReferenceIndex``, so it drives every other graphic that uses this dim. Only one
        is created per subplot.

        Parameters
        ----------
        data: ArrayProtocol or None
            n-dimensional timeseries data. The value dim holds the (x, y) of each datapoint, where x is the
            time-like coordinate.

            Ex: an array of shape ``[n_trials, n_traces, n_timepoints, 2]`` with ``dims`` of
            ``("trial", "trace", "time", "xy")`` and ``spatial_dims`` of ``("trace", "time", "xy")``.

            Pass ``None`` to create the ``NDTimeseries`` without a graphic and set the data later using
            ``nd_timeseries.data``, the slider dims then require an explicit reference range in the ``NDWidget``.

        dims: Sequence[str]
            name for every dim of ``data``, in order.

        spatial_dims: tuple[str, str, str]
            The 3 spatial dims **in display order**: ``(n_graphics, p, <value dim>)``, i.e. the number of traces
            in the collection, the number of datapoints ``p`` in each of them, and the value dim which holds the
            xy or xyz coordinate. A heatmap requires a value dim of size exactly 2. The dims do not need to be in
            this order in the array, the data slice is transposed into display order.

        args
            extra positional arguments passed to the ``processor`` constructor.

        graphic_type: type[LineCollection | LineStack | ScatterCollection | ScatterStack | ImageGraphic], default ``LineStack``
            The graphical representation used to display the data slice. ``ImageGraphic`` renders the traces as a
            heatmap, one row per trace, where the color represents the y coordinate. The x coordinates are
            applied as the offset and scale of the image, and the y values are interpolated onto a uniform x grid
            if the x sampling is not uniform.

        x_range_mode: "fixed" | "auto" | None, default "auto"
            How the camera x-range is coupled to the ``p`` dim.

            * ``None``: the camera is left alone.
            * ``"fixed"``: the x-range is set from ``display_window``, centered on the current ``p`` index, on
              every update.
            * ``"auto"``: as ``"fixed"``, and the camera x-range is also polled on every render. Panning or
              zooming then sets ``display_window`` to the new width and the ``p`` index to the new center, with
              a lower bound of 3 datapoints on the width.

            Forced to ``None`` when ``display_window`` is ``None``.

        processor: type[NDPositionsProcessor], default ``NDPositionsProcessor``
            ``NDPositionsProcessor`` subclass that manages the data and produces the data slices.

        display_window: int, float or None, default 10
            Size of the window of the ``p`` dim to render, in the reference units of that dim, centered on its
            current index. Use ``None`` to render every datapoint, which also forces ``x_range_mode`` to
            ``None``. This is what makes out-of-core rendering possible, i.e. rendering a window of a dataset
            that is larger than GPU VRAM.

        window_funcs: dict[str, tuple[WindowFuncCallable | None, int | float | None]], optional
            Per-slider-dim window functions applied around the current slider position, ex:
            ``{"trial": (np.mean, 5)}``. Each value is a ``(func, window_size)`` pair where:

            * *func* must accept ``axis: int`` and ``keepdims: bool`` kwargs (ex: ``np.mean``, ``np.max``). It
              **must** return an array that has the same dims as the input, therefore the size of any dim along
              which it was applied should reduce to ``1``. These dims must not be removed by the window func.

            * *window_size* is in reference-space units.

            Not used for the ``p`` dim, see ``datapoints_window_func``.

        window_order: tuple[str, ...], optional
            Order in which the window functions are applied across dims. Only dims listed here have their window
            function applied, ``window_funcs`` are ignored for any dim not specified in ``window_order``.

        spatial_func: Callable[[ArrayProtocol], ArrayProtocol], optional
            A function applied to the spatial slice *after* the window funcs, right before rendering.

        slider_dim_transforms: dict[str, Callable[[Any], int] | ArrayLike], optional
            Per-slider-dim mapping from reference-space values to local array indices. An array of reference
            values may be given instead of a Callable, ``searchsorted`` is then used as the transform. The
            transform for the ``p`` dim is typically the array of x values, ex: a timestamps array, so the
            slider is in seconds rather than sample indices. Any dim without a transform uses the identity
            mapping, i.e. the current reference value is rounded to the nearest integer and used as the array
            index.

        max_display_datapoints: int, default 1_000
            Maximum number of datapoints to render per graphic. The step size of the display window slice is set
            from this using floor division.

        datapoints_window_func: tuple[Callable, str, int | float], optional
            Window function applied along the ``p`` dim after the display window has been taken, as
            ``(func, apply_dims, window_size)`` where:

            * *func* must accept an ``axis: int`` kwarg (ex: ``np.mean``, ``np.max``). It is given a sliding
              window view of the data and is reduced along the window axis.

            * *apply_dims* names the coordinates of the value dim to apply it to, one of ``"all", "x", "y",
              "z", "xy", "xz", "yz", "xyz"``. Coordinates that are not named are passed through unchanged.

            * *window_size* is in the reference units of the ``p`` dim. It is mapped to array indices, clamped to
              a minimum of 3, and rounded up to an odd size.

            If used, ``display_window`` is approximate and not exact due to padding from the window size.

        colors: str | Sequence[str] | np.ndarray | FeatureCallable, optional
            Colors of the traces. Mutually exclusive with ``cmap``, setting one clears the other.

            * static, a single color for every graphic, ex: ``"cyan"`` or an RGBA sequence of 4 floats
            * static, one color per graphic, ``[n_graphics]`` of str or ``[n_graphics, 4]`` RGBA
            * windowed, one color per datapoint, ``[n_graphics, p, 4]`` RGBA
            * windowed, a ``FeatureCallable``

        cmap: str | Sequence[str], optional
            Colormap applied to the traces, always static. A single name for every graphic, or an iterable of
            ``[n_graphics]`` names for a colormap per graphic. Mutually exclusive with ``colors``. It is the only
            feature that is carried over to the heatmap representation.

        cmap_transform: np.ndarray | FeatureCallable, optional
            Values that the colormap colors are mapped from.

            * static, one value per graphic, ``[n_graphics]``, so each graphic gets a single color
            * windowed, one value per datapoint, ``[n_graphics, p]``
            * windowed, a ``FeatureCallable``

        cmap_range: (float, float) | np.ndarray, optional
            The (min, max) of ``cmap_transform`` mapped onto the colormap, or ``[n_graphics, 2]`` for a range per
            graphic. A windowed array ``cmap_transform`` defaults to its own (min, max) over the full ``p`` dim,
            so the display window keeps its position within the colormap. A ``FeatureCallable`` transform
            requires an explicit range, its full range is not knowable without evaluating it everywhere.

        thickness: float | Sequence[float], optional
            Thickness of the lines, always static. A single value for every graphic, or ``[n_graphics]`` values
            for a thickness per graphic.

        sizes: float | Sequence[float] | np.ndarray | FeatureCallable, optional
            Size of the scatter points.

            * static, a single size for every graphic, or ``[n_graphics]`` sizes for one size per graphic
            * windowed, one size per datapoint, ``[n_graphics, p]``
            * windowed, a ``FeatureCallable``

        markers: str | Sequence[str] | np.ndarray | FeatureCallable, optional
            Marker shape of the scatter points.

            * static, a single marker for every graphic, or ``[n_graphics]`` markers for one per graphic
            * windowed, one marker per datapoint, ``[n_graphics, p]``
            * windowed, a ``FeatureCallable``

        name: str, optional
            Name for this ``NDGraphic``, used to retrieve it with ``nd_subplot[name]``.

        graphic_kwargs: dict, optional
            passed to the ``graphic_type`` constructor.

        processor_kwargs: dict, optional
            passed to the ``processor`` constructor.

        Returns
        -------
        NDTimeseries

        Notes
        -----
        Each of the other graphic features is either *windowed* or *static*, decided from the value itself:

        * **windowed**: a ``FeatureCallable``, or an array whose axis 1 spans the ``p`` dim. It is re-sliced with
          the same display window slice as the data on every update, so the feature carries a value per
          displayed datapoint. An array **must** span the **full** ``p`` dim of the data, i.e.
          ``[n_graphics, p, <value dim>]``, since it is indexed with an index into the full ``p`` dim. A
          ``FeatureCallable`` is passed the data slice and that display window slice, and returns the feature
          values for the displayed datapoints.

        * **static**: anything else. It is set once on the collection, ex: a single value for every graphic,
          ``[n_graphics]`` values for one per graphic, or an iterator of per-graphic values such as
          ``itertools.cycle(["jet", "viridis"])``.

        A feature the graphic type does not have is ignored, ex: ``thickness`` for scatters, ``markers`` for
        lines. The heatmap representation uses only ``cmap``.

        """
        self._check_slider_dims(dims, spatial_dims, data, positions=True)

        nd = NDTimeseries(
            self.ndw.indices,
            self,
            data,
            dims,
            spatial_dims,
            *args,
            graphic_type=graphic_type,
            linear_selector=True,
            x_range_mode=x_range_mode,
            processor=processor,
            display_window=display_window,
            window_funcs=window_funcs,
            window_order=window_order,
            spatial_func=spatial_func,
            slider_dim_transforms=slider_dim_transforms,
            max_display_datapoints=max_display_datapoints,
            datapoints_window_func=datapoints_window_func,
            colors=colors,
            cmap=cmap,
            cmap_transform=cmap_transform,
            cmap_range=cmap_range,
            thickness=thickness,
            sizes=sizes,
            markers=markers,
            name=name,
            graphic_kwargs=graphic_kwargs,
            processor_kwargs=processor_kwargs,
        )

        self._nd_graphics.append(nd)
        return nd

    def add_nd_lines(
        self,
        data: ArrayProtocol | None,
        dims: Sequence[str],
        spatial_dims: tuple[str, str, str],
        *args,
        processor: type[NDPositionsProcessor] = NDPositionsProcessor,
        display_window: int | float | None = 10,
        window_funcs: dict[
            str, tuple[WindowFuncCallable | None, int | float | None]
        ] = None,
        window_order: tuple[str, ...] = None,
        spatial_func: Callable[[ArrayProtocol], ArrayProtocol] = None,
        slider_dim_transforms: dict[str, Callable[[Any], int] | ArrayLike] = None,
        max_display_datapoints: int = 1_000,
        datapoints_window_func: tuple[Callable, str, int | float] | None = None,
        colors: ColorsType = None,
        cmap: str | Sequence[str] = None,
        cmap_transform: np.ndarray | FeatureCallable = None,
        cmap_range: tuple[float, float] = None,
        thickness: float | Sequence[float] = None,
        name: str = None,
        graphic_kwargs: dict = None,
        processor_kwargs: dict = None,
    ) -> NDPositions:
        """
        Add n-dimensional positional data to this subplot, rendered as a ``LineCollection``.

        Every dim that is not listed in ``spatial_dims`` becomes a slider dim. The datapoints dim, ``p``, is both
        a spatial dim and a slider dim, it is windowed by ``display_window`` and ``datapoints_window_func``
        rather than by ``window_funcs``.

        Parameters
        ----------
        data: ArrayProtocol or None
            n-dimensional positional data.

            Ex: an array of shape ``[n_trials, n_keypoints, n_timepoints, 2]`` with ``dims`` of
            ``("trial", "keypoint", "time", "xy")`` and ``spatial_dims`` of ``("keypoint", "time", "xy")``.

            Pass ``None`` to create the ``NDPositions`` without a graphic and set the data later using
            ``nd_positions.data``, the slider dims then require an explicit reference range in the ``NDWidget``.

        dims: Sequence[str]
            name for every dim of ``data``, in order.

        spatial_dims: tuple[str, str, str]
            The 3 spatial dims **in display order**: ``(n_graphics, p, <value dim>)``, i.e. the number of lines
            in the collection, the number of datapoints ``p`` in each of them, and the value dim which holds the
            xy or xyz coordinate and must be of size 2 or 3. The dims do not need to be in this order in the
            array, the data slice is transposed into display order.

        args
            extra positional arguments passed to the ``processor`` constructor.

        processor: type[NDPositionsProcessor], default ``NDPositionsProcessor``
            ``NDPositionsProcessor`` subclass that manages the data and produces the data slices.

        display_window: int, float or None, default 10
            Size of the window of the ``p`` dim to render, in the reference units of that dim, centered on its
            current index. Use ``None`` to render every datapoint, or ``0`` to render only the datapoint at the
            current index. This is what makes out-of-core rendering possible, i.e. rendering a window of a
            dataset that is larger than GPU VRAM.

        window_funcs: dict[str, tuple[WindowFuncCallable | None, int | float | None]], optional
            Per-slider-dim window functions applied around the current slider position, ex:
            ``{"trial": (np.mean, 5)}``. Each value is a ``(func, window_size)`` pair where:

            * *func* must accept ``axis: int`` and ``keepdims: bool`` kwargs (ex: ``np.mean``, ``np.max``). It
              **must** return an array that has the same dims as the input, therefore the size of any dim along
              which it was applied should reduce to ``1``. These dims must not be removed by the window func.

            * *window_size* is in reference-space units.

            Not used for the ``p`` dim, see ``datapoints_window_func``.

        window_order: tuple[str, ...], optional
            Order in which the window functions are applied across dims. Only dims listed here have their window
            function applied, ``window_funcs`` are ignored for any dim not specified in ``window_order``.

        spatial_func: Callable[[ArrayProtocol], ArrayProtocol], optional
            A function applied to the spatial slice *after* the window funcs, right before rendering.

        slider_dim_transforms: dict[str, Callable[[Any], int] | ArrayLike], optional
            Per-slider-dim mapping from reference-space values to local array indices. An array of reference
            values may be given instead of a Callable, ``searchsorted`` is then used as the transform (ex: a
            timestamps array). Any dim without a transform uses the identity mapping, i.e. the current reference
            value is rounded to the nearest integer and used as the array index.

        max_display_datapoints: int, default 1_000
            Maximum number of datapoints to render per graphic. The step size of the display window slice is set
            from this using floor division.

        datapoints_window_func: tuple[Callable, str, int | float], optional
            Window function applied along the ``p`` dim after the display window has been taken, as
            ``(func, apply_dims, window_size)`` where:

            * *func* must accept an ``axis: int`` kwarg (ex: ``np.mean``, ``np.max``). It is given a sliding
              window view of the data and is reduced along the window axis.

            * *apply_dims* names the coordinates of the value dim to apply it to, one of ``"all", "x", "y",
              "z", "xy", "xz", "yz", "xyz"``. Coordinates that are not named are passed through unchanged.

            * *window_size* is in the reference units of the ``p`` dim. It is mapped to array indices, clamped to
              a minimum of 3, and rounded up to an odd size.

            If used, ``display_window`` is approximate and not exact due to padding from the window size.

        colors: str | Sequence[str] | np.ndarray | FeatureCallable, optional
            Colors of the lines. Mutually exclusive with ``cmap``, setting one clears the other.

            * static, a single color for every graphic, ex: ``"cyan"`` or an RGBA sequence of 4 floats
            * static, one color per graphic, ``[n_graphics]`` of str or ``[n_graphics, 4]`` RGBA
            * windowed, one color per datapoint, ``[n_graphics, p, 4]`` RGBA
            * windowed, a ``FeatureCallable``

        cmap: str | Sequence[str], optional
            Colormap applied to the lines, always static. A single name for every graphic, or an iterable of
            ``[n_graphics]`` names for a colormap per graphic. Mutually exclusive with ``colors``.

        cmap_transform: np.ndarray | FeatureCallable, optional
            Values that the colormap colors are mapped from.

            * static, one value per graphic, ``[n_graphics]``, so each graphic gets a single color
            * windowed, one value per datapoint, ``[n_graphics, p]``
            * windowed, a ``FeatureCallable``

        cmap_range: (float, float) | np.ndarray, optional
            The (min, max) of ``cmap_transform`` mapped onto the colormap, or ``[n_graphics, 2]`` for a range per
            graphic. A windowed array ``cmap_transform`` defaults to its own (min, max) over the full ``p`` dim,
            so the display window keeps its position within the colormap. A ``FeatureCallable`` transform
            requires an explicit range, its full range is not knowable without evaluating it everywhere.

        thickness: float | Sequence[float], optional
            Thickness of the lines, always static. A single value for every graphic, or ``[n_graphics]`` values
            for a thickness per graphic.

        name: str, optional
            Name for this ``NDGraphic``, used to retrieve it with ``nd_subplot[name]``.

        graphic_kwargs: dict, optional
            passed to the underlying ``LineCollection``

        processor_kwargs: dict, optional
            passed to the ``processor`` constructor.

        Returns
        -------
        NDPositions

        Notes
        -----
        Each of the other graphic features is either *windowed* or *static*, decided from the value itself:

        * **windowed**: a ``FeatureCallable``, or an array whose axis 1 spans the ``p`` dim. It is re-sliced with
          the same display window slice as the data on every update, so the feature carries a value per
          displayed datapoint. An array **must** span the **full** ``p`` dim of the data, i.e.
          ``[n_graphics, p, <value dim>]``, since it is indexed with an index into the full ``p`` dim. A
          ``FeatureCallable`` is passed the data slice and that display window slice, and returns the feature
          values for the displayed datapoints.

        * **static**: anything else. It is set once on the collection, ex: a single value for every graphic,
          ``[n_graphics]`` values for one per graphic, or an iterator of per-graphic values such as
          ``itertools.cycle(["jet", "viridis"])``.

        """
        self._check_slider_dims(dims, spatial_dims, data, positions=True)

        nd = NDPositions(
            self.ndw.indices,
            self,
            data,
            dims,
            spatial_dims,
            *args,
            graphic_type=LineCollection,
            processor=processor,
            display_window=display_window,
            window_funcs=window_funcs,
            window_order=window_order,
            spatial_func=spatial_func,
            slider_dim_transforms=slider_dim_transforms,
            max_display_datapoints=max_display_datapoints,
            datapoints_window_func=datapoints_window_func,
            colors=colors,
            cmap=cmap,
            cmap_transform=cmap_transform,
            cmap_range=cmap_range,
            thickness=thickness,
            name=name,
            graphic_kwargs=graphic_kwargs,
            processor_kwargs=processor_kwargs,
        )

        self._nd_graphics.append(nd)
        return nd
