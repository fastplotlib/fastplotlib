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
        spatial_dims: tuple[str, str, str],  # must be in order, last dim must be 4
        window_funcs: tuple[WindowFuncCallable | None, ...] | WindowFuncCallable = None,
        window_order: tuple[int, ...] = None,
        spatial_func: Callable[[ArrayLike], ArrayLike] = None,
        slider_dim_transforms=None,
    ):
        """
        ``NDProcessor`` subclass for n-dimensional vector data

        Produces (num_vectors, 2, [2 or 3]) slices for a ``VectorsGraphic``. The last two dimensions describe the
        position/direction and the 2D/3D spatial coordinate, respectively.

        Parameters
        ----------
        data: ArrayProtocol
            Shape [..., num_vectors, 2, 2] or [..., num_vectors, 2, 3]. data[..., 0, :] gives the positions, data[..., 1, :] gives directions

        dims: Sequence[str]
            names for each dimension in ``data``. Dimensions not listed in
            ``spatial_dims`` are treated as slider dimensions and **must** appear as
            keys in the parent ``NDWidget``'s ``ref_ranges``
                Examples::

            A custom subclass's ``data`` object doesn't necessarily need to have these dims, but the ``get()`` method
            must operate as if these dimensions exist and return an array that matches the spatial dimensions.


            dims in the array do not need to be in the order that you want to display them, for example you can have a
            weird array where the dims are interpreted as:
            ``("col", "depth", "row", "time")``, and then specify spatial_dims as ``("row", "col")``.

        spatial_dims : tuple[str, str] | tuple[str, str, str]
            The dim names that indicate [n_vectors, positions & directions, xy(z)], **in that order**

        slider_dim_transforms : dict, optional
            See :class:`NDProcessor`.

        window_funcs : dict, optional
            See :class:`NDProcessor`.

        window_order : tuple, optional
            See :class:`NDProcessor`.

        spatial_func : callable, optional
            See :class:`NDProcessor`.

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

        # Axis order of the spatial dimensions to display
        self._spatial_dims_int = tuple(
            self.spatial_dims.index(d) for d in self.dims if d in self.spatial_dims
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
    def spatial_dims(self) -> tuple[str, str]:
        """
        Spatial dims, **in order**
        Dimensions in order are num_vectors, position/direction, xy[z], so the shape is [num_vectors, 2, 2 or 3]
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
        Get the data at the given index, process data through the window functions.

        Note that we do not use __getitem__ here since the index is a tuple specifying a single integer
        index for each dimension. Slices are not allowed, therefore __getitem__ is not suitable here.

        Parameters
        ----------
        indices: tuple[int, ...]
            Get the processed data at this index. Must provide a value for each dimension.
            Example: get((100, 5))

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


        return window_output.transpose(*self._spatial_dims_int)


class NDVectors(NDGraphic):
    def __init__(
        self,
        ref_index: ReferenceIndex,
        nd_subplot: NDWSubplot,
        data: ArrayProtocol | None,
        dims: Sequence[str],
        spatial_dims: tuple[
            str, str, str
        ],  # must be in order!
        window_funcs: tuple[WindowFuncCallable | None, ...] | WindowFuncCallable = None,
        window_order: tuple[int, ...] = None,
        spatial_func: Callable[[ArrayProtocol], ArrayProtocol] = None,
        slider_dim_transforms=None,
        name: str = None,
        graphic_kwargs: dict = None,
    ):
        """
        ``NDGraphic`` subclass for n-dimensional vector rendering

        Wraps an :class:`VectorGraphic`

        Every dimension that is *not* listed in ``spatial_dims`` becomes a slider
        dimension. Each slider dim must have a ``ReferenceRange`` defined in the
        ``ReferenceIndex`` of the parent ``NDWidget``. The widget uses this to direct
        a change in the ``ReferenceIndex`` and update the graphics.

        Parameters
        ----------
        ref_index : ReferenceIndex
            The shared reference index that delivers slider updates to this graphic.

        nd_subplot : NDWSubplot
            parent ndsubplot the NDGraphic is in

        data : array-like or None
            Shape [num_vectors, 2, 2] or [num_vectors, 3, 2]. data[:, :, 0] gives the positions, data[:, :, 1] gives directions
            n-dimension image data array

        dims : sequence of hashable
            Name for every dimension of ``data``, in order. Non-spatial dims must
            match keys in ``ref_index``.

            ex: ``("time", "depth", "row", "col")`` — ``"time"`` and ``"depth"`` must
            be present in ``ref_index``.

        spatial_dims : tuple[str, str] | tuple[str, str, str]
            Spatial dimensions **in order**: These dims are either [n_vectors, 2, 2] or [n_vectors, 2, 3], indicating [n_vectors, positions & directions, xy(z)]

        window_funcs : dict, optional
            See :class:`NDProcessor`.

        window_order : tuple, optional
            See :class:`NDProcessor`.

        spatial_func : callable, optional
            See :class:`NDProcessor`.

        slider_dim_transforms : dict, optional
            See :class:`NDProcessor`.

        name : str, optional
            Name for the underlying graphic.

        See Also
        --------
        NDImageProcessor : The processor that backs this graphic.

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
        # Creates an ``ImageGraphic`` or ``ImageVolumeGraphic`` based on the number of spatial dims,
        # adds it to the subplot, and resets the camera and histogram.

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
        get or set the spatial dims **in order**.
        Spatial dim shape here is [num_vectors, position/dimension (2), xy[z] (2 or 3)]
        """
        return self.processor.spatial_dims

    @spatial_dims.setter
    def spatial_dims(self, dims: tuple[str, str, str]):
        self.processor.spatial_dims = dims

        # shape has probably changed, recreate graphic
        run_sync(self._create_graphic())

    @property
    def indices(self) -> dict[str, Any]:
        """get or set the indices, managed by the ReferenceIndex, users usually don't want to set this manually"""
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
