from concurrent.futures import Future

from ...utils import ArrayProtocol, FutureArrayProtocol


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
    """starts coroutines for async arrays in NDProcessor"""
    def start(self, *args, **kwargs):
        cr = func(self, *args, **kwargs)
        try:
            # begin coroutine
            fut: FutureArray | ArrayProtocol = cr.send(None)
        except StopIteration:
            # NDProcessor.get() was not async, nothing to return
            return

        block = kwargs.get("block", True)
        timeout = kwargs.get("timeout", 1.0)

        if block: # resolve Future immediately
            try:
                if isinstance(fut, FutureArrayProtocol):
                    # array is async, resolve future and send
                    cr.send(fut.result(timeout=timeout))
                else:
                    # not async, just return the array
                    cr.send(fut)
            except StopIteration:
                pass
        else: # no block, probably resolving multiple futures simultaneously
            if isinstance(fut, FutureArrayProtocol):
                # data is async, return coroutine generator and future
                # ReferenceIndex._render_indices() will manage them and wait to gather all futures
                return cr, fut
            else:
                # not async, just return the array
                try:
                    cr.send(fut)
                except StopIteration: # has to be here because of the yield expression, i.e. it's a generator
                    pass
    return start
