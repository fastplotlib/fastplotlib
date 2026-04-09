from collections.abc import Generator
from concurrent.futures import Future

from ...utils import ArrayProtocol, FutureProtocol, CudaArrayProtocol, cuda_to_numpy


class FutureArray(Future):
    def __init__(self, shape, dtype, timeout: float = 1.0):
        self._shape = shape
        self._dtype = dtype
        self._timeout = timeout

        super().__init__()

    @property
    def shape(self) -> tuple[int, ...]:
        return self._shape

    @property
    def ndim(self) -> int:
        return len(self.shape)

    @property
    def dtype(self) -> str:
        return self._dtype

    def __getitem__(self, item) -> ArrayProtocol:
        return self.result(self._timeout)[item]

    def __array__(self) -> ArrayProtocol:
        return self.result(self._timeout)

    def __array_ufunc__(self, ufunc, method, *inputs, **kwargs):
        raise NotImplementedError

    def __array_function__(self, func, types, *args, **kwargs):
        raise NotImplementedError


# inspired by https://www.dabeaz.com/coroutines/
def start_coroutine(func):
    """
    Starts coroutines for async arrays wrapped by NDProcessor.
    Used by all NDGraphic.set_indices and NDGraphic._create_graphic.

    It also immediately starts coroutines unless block=False is provided. It handles all the triage of possible
    sync vs. async (Future-like) objects.

    The only time when block=False is when ReferenceIndex._render_indices uses it to loop through setting all
    indices, and then collect and send the results back down to NDProcessor.get().
    """

    def start(
        self, *args, **kwargs
    ) -> tuple[Generator, ArrayProtocol | CudaArrayProtocol | FutureProtocol] | None:
        cr = func(self, *args, **kwargs)
        try:
            # begin coroutine
            to_resolve: FutureProtocol | ArrayProtocol | CudaArrayProtocol = cr.send(
                None
            )
        except StopIteration:
            # NDProcessor.get() has no `yield` expression, not async, nothing to return
            return None

        block = kwargs.get("block", True)
        timeout = kwargs.get("timeout", 1.0)

        if block:  # resolve Future immediately
            try:
                if isinstance(to_resolve, FutureProtocol):
                    # array is async, resolve future and send
                    cr.send(to_resolve.result(timeout=timeout))
                elif isinstance(to_resolve, CudaArrayProtocol):
                    # array is on GPU, it is technically and on GPU, convert to numpy array on CPU
                    cr.send(cuda_to_numpy(to_resolve))
                else:
                    # not async, just send the array
                    cr.send(to_resolve)
            except StopIteration:
                pass

        else:  # no block, probably resolving multiple futures simultaneously
            if isinstance(to_resolve, FutureProtocol):
                # data is async, return coroutine generator and future
                # ReferenceIndex._render_indices() will manage them and wait to gather all futures
                return cr, to_resolve
            elif isinstance(to_resolve, CudaArrayProtocol):
                # it is async technically, but it's a GPU array, ReferenceIndex._render_indices will manage it
                return cr, to_resolve
            else:
                # not async, just send the array
                try:
                    cr.send(to_resolve)
                except (
                    StopIteration
                ):  # has to be here because of the yield expression, i.e. it's a generator
                    pass

    return start
