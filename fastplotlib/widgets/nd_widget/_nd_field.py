from __future__ import annotations

from collections.abc import Callable, Sequence
from math import log
from typing import Any, TYPE_CHECKING

import numpy as np
from numpy.typing import ArrayLike
from rendercanvas.utils.asyncs import sleep

from ...graphics import StreamGraphic, VectorsGraphic
from ...utils import ArrayProtocol, loop
from ._async import run_in_thread_pool, run_sync
from ._base import WindowFuncCallable
from ._index import ReferenceIndices
from ._nd_vectors import NDVectors, NDVectorsSlicer

if TYPE_CHECKING:
    from ._ndw_subplot import NDWSubplot


# how much wider than the level calls for the sampled box is, as a fraction of it, so that a small
# pan within a zoom level does not expose an unsampled edge
VIEW_PAD = 0.1

# how far past a zoom level boundary the view must travel before the level goes up, in levels, so
# that a view resting on a boundary does not rebuild back and forth. it applies going up only, a
# level whose box is narrower than the view would leave an unsampled strip along the edge
LEVEL_MARGIN = 0.05


def passthrough(value: Any) -> Any:
    return value


def check_extents_mode(mode: str | None, display_dims: Sequence[str]):
    """Validate an ``extents_mode`` against the dims it would follow the camera along"""
    if mode not in (None, "auto"):
        raise ValueError(f"`extents_mode` must be None or 'auto', got: {mode!r}")

    if mode == "auto" and len(display_dims) != 2:
        raise ValueError(
            f"`extents_mode='auto'` follows the view through `x_range` and `y_range`, which are only valid "
            f"for an orthographic projection of the xy plane, so it needs exactly 2 display dims. This field "
            f"is drawn along {tuple(display_dims)}."
        )


class NDFieldSlicer(NDVectorsSlicer):
    def __init__(
        self,
        data: Callable | None,
        dims: Sequence[str],
        display_dims: Sequence[str],
        extents: dict[str, tuple[float, float]],
        resolution: int | dict[str, int] = 24,
        window_funcs: dict[
            str, tuple[WindowFuncCallable | None, int | float | None]
        ] = None,
        window_order: tuple[str, ...] = None,
        spatial_func: Callable[[ArrayLike], ArrayLike] = None,
        slider_maps: dict[str, Callable[[Any], Any]] = None,
    ):
        """
        ``NDVectorsSlicer`` subclass that evaluates a vector field instead of slicing an array.

        The field is a callable rather than data, so there is nothing to index and nothing is held in memory
        for the dims that are not drawn. The dims in ``display_dims`` are sampled on a regular grid over
        ``extents``, every other dim is a parameter of the field whose current reference value is passed in as
        a scalar. Only the samples that are drawn are ever computed, so an arbitrarily large parameter space
        costs nothing.

        Produces the same ``[n_vectors, 2, 2 | 3]`` slices as :class:`NDVectorsSlicer`, where ``n_vectors`` is
        the number of grid samples.

        Parameters
        ----------
        data: Callable or None
            The vector field. Called with one keyword argument per dim, so every dim name must be a valid
            Python identifier. The ``display_dims`` arrive as 1D float32 arrays of length ``n_vectors`` holding
            the grid sample coordinates, the slider dims arrive as scalars. It must return one component per
            display dim, each broadcastable to ``[n_vectors]``.

            Ex: a field over ``("x", "y", "t")`` drawn on ``("x", "y")`` is called as
            ``data(x=<[n] array>, y=<[n] array>, t=1.37)`` and returns ``(u, v)``.

            Non-finite components are zeroed, see :meth:`get`. Pass ``None`` to create the slicer without a
            field and set it later using :attr:`data`.

        dims: Sequence[str]
            Name for every variable of the field. Dims not listed in ``display_dims`` are slider dims and
            **must** appear as keys in the parent ``NDWidget``'s ``ranges``.

        display_dims: Sequence[str]
            The 2 or 3 dims that are visualized, **in display order**. These are the dims sampled on the grid,
            so they are also the coordinate axes of the drawing, and the field must return one component per
            display dim.

        extents: dict[str, tuple[float, float]]
            The ``(min, max)`` of the sampled grid along each display dim, one entry per display dim.

        resolution: int | dict[str, int], default 24
            Number of grid samples along each display dim, either one value for all of them or one per dim.
            The number of samples cannot change while a graphic is using the slice, so changing it recreates
            the graphic.

        spatial_func: Callable[[ArrayLike], ArrayLike], optional
            A function applied to the ``[n_vectors, 2, 2 | 3]`` slice right before rendering, ex: normalizing
            the directions so that arrow length does not encode magnitude.

        slider_maps: dict[str, Callable[[Any], Any]], optional
            Per-slider-dim mapping from a reference-space value to the value passed to the field, ex: a slider
            in degrees driving a field written in radians. Unlike :class:`NDSlicer` these are **not** mappings
            onto array indices, so they must be callables and the result is not rounded. Any dim without one
            gets its reference value unchanged.

        window_funcs: dict, optional
            Not supported, a window func reduces over array indices along a slider dim and a field has no
            array to reduce over. Use a ``spatial_func``, or write the reduction into the field.

        window_order: tuple[str, ...], optional
            Not supported, see ``window_funcs``.

        See Also
        --------
        NDVectorsSlicer : Base class with full parameter documentation.
        NDField : The ``NDGraphic`` that uses this slicer.

        """

        if window_funcs is not None or window_order is not None:
            raise ValueError(
                "`window_funcs` reduce over array indices along a slider dim, and a field has no array to "
                "reduce over. Use a `spatial_func`, or write the reduction into the field itself."
            )

        # set by _build_grid() once dims, display_dims, extents and resolution are all known
        self._extents: dict[str, tuple[float, float]] | None = None
        self._resolution: dict[str, int] | None = None
        self._axis_values: dict[str, np.ndarray] | None = None
        self._positions: np.ndarray | None = None
        self._n_nonfinite = 0

        super().__init__(
            data=data,
            dims=dims,
            display_dims=display_dims,
            slider_maps=slider_maps,
            spatial_func=spatial_func,
        )

        self.resolution = resolution
        self.extents = extents

    @property
    def data(self) -> Callable | None:
        """get or set the vector field, see the class docstring for the call signature"""
        return self._data

    @data.setter
    def data(self, data: Callable | None):
        if data is None:
            # no graphic is rendered until the field is set, see ``NDSlicer.data``
            self._data = None
            return

        if not callable(data):
            raise TypeError(
                f"`data` must be a callable that evaluates the field, or `None`. You passed a: {type(data)}"
            )

        self._data = data

    @property
    def display_dims(self) -> tuple[str, ...]:
        """
        Get or set the 2 or 3 dims that are visualized, **in display order**. These are the dims sampled on
        the grid, and the field returns one component per display dim.
        """
        return self._display_dims

    @display_dims.setter
    def display_dims(self, sdims: Sequence[str]):
        sdims = tuple(sdims)

        for dim in sdims:
            if dim not in self.dims:
                raise KeyError(
                    f"display dim '{dim}' is not one of the field's dims: {self.dims}"
                )

        if len(sdims) not in (2, 3):
            raise ValueError(
                f"a field is visualized along 2 or 3 of its dims, you passed {len(sdims)}: {sdims}"
            )

        self._display_dims = sdims
        self._build_grid()

    @property
    def extents(self) -> dict[str, tuple[float, float]]:
        """
        Get or set the ``(min, max)`` of the sampled grid along each display dim. Setting them resamples the
        field over the new grid.
        """
        return self._extents

    @extents.setter
    def extents(self, extents: dict[str, tuple[float, float]]):
        if set(extents.keys()) != set(self.display_dims):
            raise KeyError(
                f"`extents` must have one entry per display dim, {self.display_dims}. "
                f"You passed: {sorted(extents.keys())}"
            )

        parsed = dict()
        for dim in self.display_dims:
            low, high = (float(v) for v in extents[dim])

            if not high > low:
                raise ValueError(
                    f"`extents` along '{dim}' must be (min, max) with min < max, you passed: {extents[dim]}"
                )

            parsed[dim] = (low, high)

        self._extents = parsed
        self._build_grid()

    @property
    def resolution(self) -> dict[str, int]:
        """
        Get or set the number of grid samples along each display dim. Setting it resamples the field, and
        since the number of samples cannot change in place it also recreates the graphic.
        """
        return self._resolution

    @resolution.setter
    def resolution(self, resolution: int | dict[str, int]):
        if not isinstance(resolution, dict):
            resolution = {dim: resolution for dim in self.display_dims}

        elif set(resolution.keys()) != set(self.display_dims):
            raise KeyError(
                f"`resolution` must be one value, or a dict with one entry per display dim, "
                f"{self.display_dims}. You passed: {sorted(resolution.keys())}"
            )

        parsed = dict()
        for dim in self.display_dims:
            n = int(resolution[dim])

            if n < 2:
                # the streamline integrator needs a spacing along every sampled axis
                raise ValueError(
                    f"`resolution` along '{dim}' must be at least 2, you passed: {resolution[dim]}"
                )

            parsed[dim] = n

        self._resolution = parsed
        self._build_grid()

    def _build_grid(self):
        # regular grid over the extents, raveled so it maps straight onto the [n_vectors, ...] slice.
        # called by every setter that changes the grid, and skipped until they have all been set
        if self._extents is None or self._resolution is None:
            return

        axes = [
            np.linspace(*self._extents[dim], self._resolution[dim], dtype=np.float32)
            for dim in self.display_dims
        ]

        # "ij" so that mesh[i] corresponds to display_dims[i], and so positions[:, i] does too
        mesh = [m.ravel() for m in np.meshgrid(*axes, indexing="ij")]

        self._axis_values = dict(zip(self.display_dims, mesh))
        self._positions = np.stack(mesh, axis=1)

    @property
    def positions(self) -> np.ndarray | None:
        """the grid sample coordinates the field is evaluated at, shape ``[n_vectors, 2 | 3]``"""
        return self._positions

    @property
    def n_vectors(self) -> int:
        """number of grid samples, i.e. the product of the resolution along each display dim"""
        return self._positions.shape[0]

    @property
    def n_nonfinite(self) -> int:
        """
        How many of the vectors in the last slice the field returned as non-finite, and were therefore zeroed.

        Non-zero means the grid has samples at or near a pole of the field. Those vectors are not drawn.
        """
        return self._n_nonfinite

    @property
    def shape(self) -> dict[str, int]:
        """
        Number of grid samples along each display dim. The slider dims are absent because a field parameter is
        continuous and has no size.
        """
        return dict(self._resolution)

    @property
    def ndim(self) -> int:
        """number of dims, i.e. the number of variables of the field"""
        return len(self.dims)

    @property
    def slider_maps(self) -> dict[str, Callable[[Any], Any]]:
        """
        Get or set the per-slider-dim mapping from a reference-space value to the value passed to the field.

        Unlike :class:`NDSlicer` these do not map onto array indices, so they must be callables and the result
        is not rounded. Any dim without one gets its reference value unchanged.
        """
        return self._index_mappings

    @slider_maps.setter
    def slider_maps(self, maps: dict[str, Callable[[Any], Any] | None] | None):
        if maps is None:
            self._index_mappings = {d: passthrough for d in self.dims}
            return

        for d in maps.keys():
            if d not in self.dims:
                raise KeyError(
                    f"`slider_maps` provided for non-existent dim: {d}, existing dims are: {self.dims}"
                )

            if maps[d] is None:
                maps[d] = passthrough

            elif not callable(maps[d]):
                raise TypeError(
                    f"`slider_maps` for a field map a reference-space value onto the value passed to the "
                    f"field, not onto an array index, so they must be callables. An array of reference values "
                    f"would quantize the parameter onto its entries. You passed a {type(maps[d])} for '{d}'."
                )

        for d in self.dims:
            # fill in any unspecified maps
            if d not in maps.keys():
                maps[d] = passthrough

        self._index_mappings = maps

    def _evaluate(self, values: dict[str, Any]) -> np.ndarray:
        # runs in the thread pool, see get()
        components = self.data(**values)

        n, n_coords = self._positions.shape

        if len(components) != n_coords:
            raise ValueError(
                f"the field must return one component per display dim, {self.display_dims}, so "
                f"{n_coords} of them. It returned {len(components)}."
            )

        directions = np.empty_like(self._positions)
        for i, component in enumerate(components):
            directions[:, i] = np.broadcast_to(
                np.asarray(component, dtype=np.float32), (n,)
            )

        # a pole in the field gives a non-finite vector, which becomes a nan transform matrix on a
        # VectorsGraphic and a nan streamline on a StreamGraphic. zero the whole vector, not just the
        # non-finite component, so that it is simply not drawn rather than pointing somewhere wrong
        nonfinite = ~np.isfinite(directions).all(axis=1)
        self._n_nonfinite = int(nonfinite.sum())
        directions[nonfinite] = 0.0

        return np.stack([self._positions, directions], axis=1)

    async def get(self, indices: dict[str, Any]) -> np.ndarray:
        """
        Evaluate the field over the grid at the given indices.

        The display dims are passed in as the grid sample coordinates and the slider dims as scalars, mapped
        through the ``slider_maps``. Vectors the field returns as non-finite are zeroed, and :attr:`n_nonfinite`
        reports how many there were.

        Parameters
        ----------
        indices: dict[str, Any]
            Reference-space value for each slider dim, ex: ``{"t": 1.37}``. Must provide a value for every
            slider dim.

        Returns
        -------
        np.ndarray
            data slice of shape ``[n_vectors, 2 | 3]``, index ``0`` along the second dim holding the grid
            sample positions and index ``1`` the field vector at each of them

        """
        values = dict(self._axis_values)
        for dim in self.slider_dims:
            values[dim] = self.slider_maps[dim](indices[dim])

        # the field is user code of unknown cost, so it never runs on the render loop
        data_slice = await run_in_thread_pool(self._executor, self._evaluate, values)

        if self.spatial_func is not None:
            data_slice = await run_in_thread_pool(
                self._executor, self._spatial_func, data_slice
            )

            if data_slice.shape != (self.n_vectors, 2, len(self.display_dims)):
                raise ValueError(
                    f"`spatial_func` must return an array of the same shape it is given, "
                    f"{(self.n_vectors, 2, len(self.display_dims))}, it returned {data_slice.shape}"
                )

        return data_slice


class NDField(NDVectors):
    def __init__(
        self,
        ref_index: ReferenceIndices,
        nd_subplot: NDWSubplot,
        data: Callable | None,
        dims: Sequence[str],
        display_dims: Sequence[str],
        extents: dict[str, tuple[float, float]],
        resolution: int | dict[str, int] = 24,
        extents_mode: str | None = None,
        zoom_factor: float = 2.0,
        debounce: float = 0.2,
        spatial_func: Callable[[ArrayProtocol], ArrayProtocol] = None,
        slider_maps: dict[str, Callable[[Any], Any]] = None,
        graphic_type: type[VectorsGraphic | StreamGraphic] = StreamGraphic,
        slicer: type[NDFieldSlicer] = NDFieldSlicer,
        name: str = None,
        graphic_kwargs: dict = None,
        slicer_kwargs: dict = None,
    ):
        """
        ``NDVectors`` subclass that draws a vector field given as an equation rather than as data.

        Uses an :class:`NDFieldSlicer`, which evaluates the field over a grid instead of slicing an array, and
        adds :attr:`extents_mode` so that the sampled grid can follow the camera.

        Parameters
        ----------
        ref_index : ReferenceIndices
            The shared reference index that delivers slider updates to this graphic.

        nd_subplot : NDWSubplot
            parent NDWSubplot the NDGraphic is in

        data : Callable or None
            The vector field, see :class:`NDFieldSlicer` for the call signature.

        dims : Sequence[str]
            Name for every variable of the field. Every dim that is not in ``display_dims`` becomes a slider
            dim and must have a reference range in the parent ``NDWidget``.

        display_dims : Sequence[str]
            The 2 or 3 dims that are visualized, **in display order**.

        extents : dict[str, tuple[float, float]]
            The ``(min, max)`` the field is sampled over along each display dim, one entry per display dim.
            The field is never evaluated outside these, including under ``extents_mode="auto"``.

        resolution : int | dict[str, int], default 24
            Number of grid samples along each display dim. Held constant as the extents move, so it is the
            sample spacing that changes with zoom, not the number of samples.

        extents_mode : "auto" or None, default ``None``
            How the sampled extents are coupled to the camera.

            * ``None``: the extents are fixed at what was passed.

            * ``"auto"``: the extents follow the view, quantized to zoom levels. Each level covers a factor of
              ``zoom_factor`` in view width, and the extents are resampled only when the view crosses into
              another level or pans off the sampled grid, so zooming within a level costs nothing. Requires 2
              display dims, since it reads ``x_range`` and ``y_range``.

              Resampling is not free, so leave ``separating_distance`` and ``size`` unset in ``graphic_kwargs``
              and let a ``StreamGraphic`` derive them from the sample spacing, otherwise the streamline density
              stays fixed in world space and the view empties out as you zoom in. For the same reason set
              ``cmap_range`` explicitly if the colors need to be comparable across zoom levels, since it
              otherwise re-derives from the magnitudes in each new grid.

        zoom_factor : float, default 2.0
            Ratio in view width between consecutive zoom levels, i.e. how far you have to zoom before the
            sampling changes. Only used when ``extents_mode`` is ``"auto"``.

        debounce : float, default 0.2
            Seconds the view must be still before the extents are resampled. A resample re-evaluates the field
            and, for a ``StreamGraphic``, places every streamline again, which is far too expensive to do while
            a zoom or pan gesture is still in progress. Only used when ``extents_mode`` is ``"auto"``.

        spatial_func : Callable[[ArrayProtocol], ArrayProtocol], optional
            A function applied to the data slice right before rendering, see :class:`NDFieldSlicer`.

        slider_maps : dict[str, Callable[[Any], Any]], optional
            Per-slider-dim mapping from a reference-space value onto the value passed to the field, see
            :class:`NDFieldSlicer`.

        graphic_type : type[VectorsGraphic | StreamGraphic], default ``StreamGraphic``
            Graphical representation of the field. Can be changed at runtime with :attr:`graphic_type`.

        slicer : type[NDFieldSlicer], default ``NDFieldSlicer``
            The slicer type that evaluates the field.

        name : str, optional
            Name for this ``NDGraphic``, used to retrieve it with ``nd_subplot[name]``.

        graphic_kwargs : dict, optional
            passed to the underlying ``graphic_type``, ex: ``{"cmap": "viridis"}``

        slicer_kwargs : dict, optional
            passed to the ``slicer`` constructor.

        See Also
        --------
        NDFieldSlicer : The slicer that evaluates the field.

        """
        # checked before the graphic is built, so a bad mode does not leave one in the subplot
        check_extents_mode(extents_mode, display_dims)

        if slicer_kwargs is None:
            slicer_kwargs = dict()

        super().__init__(
            ref_index,
            nd_subplot=nd_subplot,
            data=data,
            dims=dims,
            display_dims=display_dims,
            spatial_func=spatial_func,
            slider_maps=slider_maps,
            graphic_type=graphic_type,
            slicer=slicer,
            name=name,
            graphic_kwargs=graphic_kwargs,
            slicer_kwargs={
                "extents": extents,
                "resolution": resolution,
                **slicer_kwargs,
            },
        )

        # the field is never sampled outside the extents it was given, so these bound every level
        self._base_extents = dict(self.slicer.extents)
        self._zoom_level = 0

        self.zoom_factor = zoom_factor
        self.debounce = debounce

        # view state for the animation func, and the revision that the debounce task waits on
        self._last_view: tuple | None = None
        self._view_rev = 0
        self._resample_scheduled = False

        self._extents_mode = None
        self.extents_mode = extents_mode

    @property
    def slicer(self) -> NDFieldSlicer:
        """NDSlicer that holds the field and evaluates it over the grid"""
        return self._slicer

    @property
    def extents(self) -> dict[str, tuple[float, float]]:
        """
        Get or set the ``(min, max)`` the field is sampled over along each display dim. Setting them makes
        these the bounds for every zoom level and resamples the field.
        """
        return self.slicer.extents

    @extents.setter
    def extents(self, extents: dict[str, tuple[float, float]]):
        self.slicer.extents = extents
        self._base_extents = dict(self.slicer.extents)
        self._zoom_level = 0

        run_sync(self._create_graphic())

    @property
    def resolution(self) -> dict[str, int]:
        """
        Get or set the number of grid samples along each display dim. Setting it recreates the graphic, since
        neither representation can change its number of samples in place.
        """
        return self.slicer.resolution

    @resolution.setter
    def resolution(self, resolution: int | dict[str, int]):
        self.slicer.resolution = resolution
        run_sync(self._create_graphic())

    @property
    def zoom_level(self) -> int:
        """
        The zoom level the sampled extents are currently at, ``0`` at the extents the field was given and one
        higher for every factor of :attr:`zoom_factor` zoomed in past them.
        """
        return self._zoom_level

    @property
    def zoom_factor(self) -> float:
        """Get or set the ratio in view width between consecutive zoom levels"""
        return self._zoom_factor

    @zoom_factor.setter
    def zoom_factor(self, zoom_factor: float):
        zoom_factor = float(zoom_factor)

        if zoom_factor <= 1:
            raise ValueError(
                f"`zoom_factor` must be > 1, you passed: {zoom_factor}. It is the ratio in view width "
                f"between consecutive zoom levels."
            )

        self._zoom_factor = zoom_factor

    @property
    def debounce(self) -> float:
        """Get or set the seconds the view must be still before the extents are resampled"""
        return self._debounce

    @debounce.setter
    def debounce(self, debounce: float):
        debounce = float(debounce)

        if debounce < 0:
            raise ValueError(f"`debounce` must be >= 0, you passed: {debounce}")

        self._debounce = debounce

    @property
    def extents_mode(self) -> str | None:
        """
        Get or set how the sampled extents are coupled to the camera.

        * ``None``: the extents are fixed.

        * ``"auto"``: the extents follow the view, quantized to zoom levels of :attr:`zoom_factor` and
          resampled once the view has been still for :attr:`debounce` seconds. Requires 2 display dims.
        """
        return self._extents_mode

    @extents_mode.setter
    def extents_mode(self, mode: str | None):
        check_extents_mode(mode, self.display_dims)

        if mode == self._extents_mode:
            return

        subplot = self._nd_subplot.subplot

        if self._extents_mode == "auto":
            subplot.remove_animation(self._on_view_change)
            self._last_view = None

        if mode == "auto":
            # seed so the first tick does not fire spuriously
            self._last_view = (subplot.x_range, subplot.y_range)
            subplot.add_animations(self._on_view_change)

        self._extents_mode = mode

    def _on_view_change(self):
        # animation func, called once per render cycle, so all it does is notice that the view moved
        # and hand off to the debounce task. resampling here would rebuild on every frame of a gesture
        if self._graphic is None:
            return

        subplot = self._nd_subplot.subplot
        view = (subplot.x_range, subplot.y_range)

        if view == self._last_view:
            return

        self._last_view = view
        self._view_rev += 1

        if not self._resample_scheduled:
            self._resample_scheduled = True
            loop.add_task(self._resample_when_settled, name="ndw-field-resample")

    async def _resample_when_settled(self):
        # wait for the view to stop moving, resample once, and go back to waiting if it moved again
        # while we were resampling. one of these runs per gesture, not per frame
        try:
            while True:
                rev = self._view_rev
                await sleep(self._debounce)

                if rev != self._view_rev:
                    # still moving
                    continue

                await self._resample()

                if rev == self._view_rev:
                    return
        finally:
            self._resample_scheduled = False

    async def _resample(self):
        if self._graphic is None or self.data is None:
            return

        subplot = self._nd_subplot.subplot
        view = dict(zip(self.display_dims, (subplot.x_range, subplot.y_range)))

        level = self._level_for(view)

        if level == self._zoom_level and self._extents_cover(view):
            # same sampling density and the view is still on the grid, nothing to do
            return

        self._zoom_level = level
        self.slicer.extents = self._extents_for(view, level)

        # the sample spacing has changed, so the streamline separation and arrow size derived from it
        # have too. building a new graphic re-derives them and places the streamlines once, where
        # setting positions, directions and the layout properties in turn would place them each time.
        # adding a graphic centers the camera on it, which would undo the zoom that got us here
        camera_state = subplot.camera.get_state()
        await self._create_graphic()
        subplot.camera.set_state(camera_state)

    def _level_for(self, view: dict[str, tuple[float, float]]) -> int:
        # zoom level of a view. measured against the width of the level 0 box rather than of the
        # field, i.e. on the same scale the boxes are on, so that the box of the level this returns
        # is between once and `zoom_factor` times the view. measuring against the field instead
        # leaves the box a further VIEW_PAD too wide at every level, and the streamlines that gain
        # brings back at a level boundary are then spent on the part of the box that is off screen
        dim = self.display_dims[0]
        width = abs(view[dim][1] - view[dim][0])

        if width <= 0:
            return self._zoom_level

        base_low, base_high = self._base_extents[dim]
        raw = log((base_high - base_low) * (1 + 2 * VIEW_PAD) / width) / log(
            self._zoom_factor
        )

        # the margin is on the way up only: going down as soon as the level's box would be narrower
        # than the view keeps the box covering the view, and the band between the two still stops a
        # view resting on a boundary from rebuilding back and forth
        level = self._zoom_level
        while raw >= level + 1 + LEVEL_MARGIN:
            level += 1
        while level > 0 and raw < level:
            level -= 1

        return level

    def _extents_cover(self, view: dict[str, tuple[float, float]]) -> bool:
        # whether the sampled grid still spans everything of the field that is in view
        for dim, (low, high) in self.slicer.extents.items():
            base_low, base_high = self._base_extents[dim]
            view_low, view_high = sorted(view[dim])

            visible_low = max(view_low, base_low)
            visible_high = min(view_high, base_high)

            if visible_high <= visible_low:
                # no part of the field is in view along this dim, so there is nothing to sample
                return True

            if visible_low < low or visible_high > high:
                return False

        return True

    def _extents_for(
        self, view: dict[str, tuple[float, float]], level: int
    ) -> dict[str, tuple[float, float]]:
        # a box of the width this zoom level calls for, centered on the view and slid to stay inside
        # the field. the width comes from the level and not from the view, so the sample spacing, and
        # the streamline separation and arrow size derived from it, change only when the level does
        extents = dict()
        scale = (1 + 2 * VIEW_PAD) / self._zoom_factor**level

        for dim in self.display_dims:
            base_low, base_high = self._base_extents[dim]
            base_width = base_high - base_low

            width = min(base_width * scale, base_width)
            half = width / 2

            center = (view[dim][0] + view[dim][1]) / 2
            center = min(max(center, base_low + half), base_high - half)

            extents[dim] = (center - half, center + half)

        return extents
