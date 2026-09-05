from __future__ import annotations

from collections.abc import Sequence, Callable
from typing import Any, TYPE_CHECKING

from numpy.typing import ArrayLike

from ...utils import (
    ARRAY_LIKE_ATTRS,
    ArrayProtocol,
    CudaArrayProtocol,
    cuda_to_numpy,
)
from ...graphics import VectorsGraphic
from ._base import (
    NDProcessor,
    NDGraphic,
    WindowFuncCallable,
)
from ._index import ReferenceIndex
from ._async import run_in_thread_pool, run_sync

if TYPE_CHECKING:
    from ._ndw_subplot import NDWSubplot


class NDVectorsProcessor(NDProcessor):
    def __init__(
        self,
        data: ArrayProtocol | None,
        dims: Sequence[str],
        spatial_dims: tuple[str, str, str],  # must be in order! [n_vectors, positions & directions, xy(z)]
        window_funcs: dict[
            str, tuple[WindowFuncCallable | None, int | float | None]
        ] = None,
        window_order: tuple[str, ...] = None,
        spatial_func: Callable[[ArrayLike], ArrayLike] = None,
        slider_dim_transforms: dict[str, Callable[[Any], int] | ArrayLike] = None,
    ):
        """
        ``NDProcessor`` subclass for n-dimensional vector data.

        Produces ``[n_vectors, 2, 2 | 3]`` slices for a ``VectorsGraphic``. The last two dims describe the
        position/direction and the 2D/3D spatial coordinate, respectively.

        Parameters
        ----------
        data: ArrayProtocol
            n-dimensional vector data, must have 3 or more dims. Index ``0`` along the positions/directions dim
            gives the vector positions and index ``1`` gives the vector directions.

            Ex: an electric field sampled over time, an array of shape ``[n_timepoints, n_vectors, 2, 2]`` with
            ``dims`` of ``("time", "n_vectors", "pos_dir", "xy")`` and ``spatial_dims`` of
            ``("n_vectors", "pos_dir", "xy")``.

        dims: Sequence[str]
            names for each dimension in ``data``. Dimensions not listed in
            ``spatial_dims`` are treated as slider dimensions and **must** appear as
            keys in the parent ``NDWidget``'s ``ref_ranges``.

            dims in the array do not need to be in the order that you want to display them, the data slice is
            transposed into the order given by ``spatial_dims``.

        spatial_dims : tuple[str, str, str]
            The 3 spatial dims **in display order**: ``(n_vectors, positions & directions, xy(z))``. The
            positions/directions dim must be of size 2 and the coordinate dim of size 2 or 3.

        slider_dim_transforms : dict[str, Callable[[Any], int] | ArrayLike], optional
            Per-slider-dim mapping from reference-space values to local array indices, see
            :class:`NDProcessor`.

        window_funcs : dict[str, tuple[WindowFuncCallable | None, int | float | None]], optional
            Per-slider-dim window functions applied around the current slider position, see
            :class:`NDProcessor`.

        window_order : tuple[str, ...], optional
            Order in which the window functions are applied across dims. Only dims listed here have their window
            function applied, see :class:`NDProcessor`.

        spatial_func : Callable[[ArrayProtocol], ArrayProtocol], optional
            A function applied to the spatial slice *after* the window funcs, right before rendering.

        See Also
        --------
            NDProcessor : Base class with full parameter documentation.
            NDVectors : The ``NDGraphic`` that uses this processor by default.
        """

        super().__init__(
            data=data,
            dims=dims,
            spatial_dims=spatial_dims,
            slider_dim_transforms=slider_dim_transforms,
            window_funcs=window_funcs,
            window_order=window_order,
            spatial_func=spatial_func,
        )

    @property
    def data(self) -> ArrayProtocol | None:
        """
        get or set managed data. If setting with new data, the new data is interpreted
        to have the same dims (i.e. same dim names and ordering of dims).
        """
        return self._data

    @data.setter
    def data(self, data: ArrayProtocol):
        if not isinstance(data, ArrayProtocol):
            # check that it's generally array-like
            raise TypeError(
                f"`data` arrays must have all of the following attributes to be sufficiently array-like:\n"
                f"{ARRAY_LIKE_ATTRS}, or they must be `None`"
            )

        if data.ndim < 3:
            raise ValueError(
                f"Shape must be (..., num_vecs, 2, [2 or 3]) you passed an array of shape {data.shape}"
            )

        self._data = data

    @property
    def spatial_dims(self) -> tuple[str, str, str]:
        """
        Spatial dims, **in display order**: ``(n_vectors, positions & directions, xy(z))``, so the data slice is
        of shape ``[n_vectors, 2, 2 | 3]``
        """
        return self._spatial_dims

    @spatial_dims.setter
    def spatial_dims(self, sdims: tuple[str, str, str]):
        for dim in sdims:
            if dim not in self.dims:
                raise KeyError

        if len(sdims) != 3:
            raise ValueError(
                f"There must be exactly 3 spatial dims for vectors indicating [num_vectors, 2, 2] or [num_vectors, 2, 3] "
            )

        self._spatial_dims = tuple(sdims)

        if self.shape[self.spatial_dims[-2]] != 2 or self.shape[
            self.spatial_dims[-1]
        ] not in (2, 3):
            raise ValueError(
                f"Spatial dimensions must haves shape (num_vecs, 2, [2 or 3]) you passed {sdims}"
            )

    async def get(self, indices: dict[str, Any]) -> ArrayProtocol:
        """
        Get the data slice at the given indices, applying the window functions and the spatial func.

        Note that we do not use __getitem__ here since the indices are reference-space values keyed by slider dim
        name, not array indices. Slices are not allowed, therefore __getitem__ is not suitable here.

        Parameters
        ----------
        indices: dict[str, Any]
            Reference-space value for each slider dim, ex: ``{"time": 46.397}``. Must provide a value for every
            slider dim.

        Returns
        -------
        ArrayProtocol
            data slice of shape ``[n_vectors, 2, 2 | 3]``, transposed into the ``spatial_dims`` display order

        """
        # this will be squeezed output, with dims in the order of self.dims
        window_output = await self.get_window_output(indices)

        # apply spatial_func; CUDA arrays run inline, numpy goes through the thread pool
        if self.spatial_func is not None:
            if isinstance(window_output, CudaArrayProtocol):
                window_output = self._spatial_func(window_output)
            else:
                window_output = await run_in_thread_pool(
                    self._executor, self._spatial_func, window_output
                )
            if window_output.ndim != len(self.spatial_dims):
                raise ValueError

        # final CUDA -> numpy conversion at the end of the pipeline
        if isinstance(window_output, CudaArrayProtocol):
            window_output = await run_in_thread_pool(self._executor, cuda_to_numpy, window_output)

        return window_output.transpose(*self.spatial_dims_indices)


class NDVectors(NDGraphic):
    def __init__(
        self,
        ref_index: ReferenceIndex,
        nd_subplot: NDWSubplot,
        data: ArrayProtocol | None,
        dims: Sequence[str],
        spatial_dims: tuple[
            str, str, str
        ],  # must be in order! [n_vectors, positions & directions, xy(z)]
        window_funcs: dict[
            str, tuple[WindowFuncCallable | None, int | float | None]
        ] = None,
        window_order: tuple[str, ...] = None,
        spatial_func: Callable[[ArrayProtocol], ArrayProtocol] = None,
        slider_dim_transforms: dict[str, Callable[[Any], int] | ArrayLike] = None,
        name: str = None,
        graphic_kwargs: dict = None,
    ):
        """
        ``NDGraphic`` subclass for n-dimensional vector rendering.

        Uses an :class:`NDVectorsProcessor` to produce the data slices and manages a :class:`.VectorsGraphic`.

        Every dimension that is *not* listed in ``spatial_dims`` becomes a slider
        dimension. Each slider dim must have a ``ReferenceRange`` defined in the
        ``ReferenceIndex`` of the parent ``NDWidget``. The widget uses this to direct
        a change in the ``ReferenceIndex`` and update the graphics.

        Parameters
        ----------
        ref_index : ReferenceIndex
            The shared reference index that delivers slider updates to this graphic.

        nd_subplot : NDWSubplot
            parent NDWSubplot the NDGraphic is in

        data : array-like or None
            n-dimensional vector data, must have 3 or more dims. Index ``0`` along the positions/directions dim
            gives the vector positions and index ``1`` gives the vector directions.

            Ex: an electric field sampled over time, an array of shape ``[n_timepoints, n_vectors, 2, 2]`` with
            ``dims`` of ``("time", "n_vectors", "pos_dir", "xy")`` and ``spatial_dims`` of
            ``("n_vectors", "pos_dir", "xy")``.

            Pass ``None`` to create the ``NDVectors`` without a graphic and set the data later using
            :attr:`data`.

        dims : Sequence[str]
            Name for every dimension of ``data``, in order. Non-spatial dims must match keys in ``ref_index``.

        spatial_dims : tuple[str, str, str]
            The 3 spatial dims **in display order**: ``(n_vectors, positions & directions, xy(z))``. The
            positions/directions dim must be of size 2 and the coordinate dim of size 2 or 3.

        window_funcs : dict[str, tuple[WindowFuncCallable | None, int | float | None]], optional
            Per-slider-dim window functions applied around the current slider position, see
            :class:`NDProcessor`.

        window_order : tuple[str, ...], optional
            Order in which the window functions are applied across dims. Only dims listed here have their window
            function applied, see :class:`NDProcessor`.

        spatial_func : Callable[[ArrayProtocol], ArrayProtocol], optional
            A function applied to the spatial slice *after* the window funcs, right before rendering.

        slider_dim_transforms : dict[str, Callable[[Any], int] | ArrayLike], optional
            Per-slider-dim mapping from reference-space values to local array indices, see
            :class:`NDProcessor`.

        name : str, optional
            Name for this ``NDGraphic``, used to retrieve it with ``nd_subplot[name]``.

        graphic_kwargs : dict, optional
            passed to the underlying :class:`.VectorsGraphic`, ex: ``{"color": "cyan", "size": 0.5}``

        See Also
        --------
        NDVectorsProcessor : The processor that produces the data slices for this graphic.

        """

        if not (set(dims) - set(spatial_dims)).issubset(ref_index.dims):
            raise IndexError(
                f"all specified `dims` must either be a spatial dim or a slider dim "
                f"specified in the NDWidget ref_ranges, provided dims: {dims}, "
                f"spatial_dims: {spatial_dims}. Specified NDWidget ref_ranges: {ref_index.dims}"
            )

        super().__init__(nd_subplot, name)

        self._ref_index = ref_index

        self._processor = NDVectorsProcessor(
            data,
            dims=dims,
            spatial_dims=spatial_dims,
            window_funcs=window_funcs,
            window_order=window_order,
            spatial_func=spatial_func,
            slider_dim_transforms=slider_dim_transforms,
        )

        self._graphic: VectorsGraphic | None = None

        if graphic_kwargs is None:
            self._graphic_kwargs = dict()
        else:
            self._graphic_kwargs = graphic_kwargs

        # create a graphic
        run_sync(self._create_graphic())

    @property
    def processor(self) -> NDVectorsProcessor:
        """NDProcessor that manages the data and produces data slices to display"""
        return self._processor

    @property
    def graphic(
        self,
    ) -> VectorsGraphic:
        """Underlying Graphic object used to display the current data slice"""
        return self._graphic

    async def _create_graphic(self):
        # Creates a ``VectorsGraphic`` from the current data slice, replacing any existing one, and adds it
        # to the subplot.

        if self.processor.data is None:
            # no graphic if data is None, useful for initializing in null states when we want to set data later
            return

        # get the data slice for this index
        # this will only have the dims specified by ``spatial_dims``
        data_slice = await self.processor.get(self.indices)

        old_graphic = self._graphic
        # check if we are replacing a graphic
        if old_graphic is not None:
            # delete the old graphic
            self._nd_subplot.subplot.delete_graphic(old_graphic)

        # create the new graphic
        self._graphic = VectorsGraphic(
            positions=data_slice[:, 0],
            directions=data_slice[:, 1],
            **self._graphic_kwargs
        )

        self._nd_subplot.subplot.add_graphic(self._graphic)

    @property
    def spatial_dims(self) -> tuple[str, str, str]:
        """
        Get or set the spatial dims **in display order**: ``(n_vectors, positions & directions, xy(z))``, so the
        data slice is of shape ``[n_vectors, 2, 2 | 3]``. Setting them recreates the graphic.
        """
        return self.processor.spatial_dims

    @spatial_dims.setter
    def spatial_dims(self, dims: tuple[str, str, str]):
        self.processor.spatial_dims = dims

        # shape has probably changed, recreate graphic
        run_sync(self._create_graphic())

    @property
    def indices(self) -> dict[str, Any]:
        """the current index of each slider dim in reference-space units, from the ``ReferenceIndex``"""
        return {d: self._ref_index[d] for d in self.processor.slider_dims}

    async def _set_indices_(self, indices: dict[str, Any] = None):
        if indices is None:
            # use latest indices if None, else use passed indices from schedule time
            indices = self.indices

        data_slice = await self.processor.get(indices)
        self.graphic.positions = data_slice[:, 0]
        self.graphic.directions = data_slice[:, 1]

        self._last_indices = indices

    @property
    def spatial_func(self) -> Callable[[ArrayProtocol], ArrayProtocol] | None:
        """get or set the spatial_func, see docstring for details"""
        # this is here even though it's the same in the base class since we can't create the image specific setter
        # without also defining the property in this subclass.
        return self.processor.spatial_func

    @spatial_func.setter
    def spatial_func(
        self, func: Callable[[ArrayProtocol], ArrayProtocol]
    ) -> Callable | None:
        self.processor.spatial_func = func
