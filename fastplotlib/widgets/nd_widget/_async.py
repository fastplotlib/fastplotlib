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


def start_coroutine(func):
    def start(self, *args, **kwargs):
        cr = func(self, *args, **kwargs)
        try:
            fut = cr.send(None)
        except StopIteration:
            # NDProcessor.get() was not async
            return

        if "block" in kwargs:
            block = kwargs["block"]
        else:
            block = True

        if "timeout" in kwargs:
            timeout = kwargs["timeout"]
        else:
            timeout = 1.0

        if block:
            # resolve Future immediately
            try:
                if isinstance(fut, FutureArrayProtocol):
                    cr.send(fut.result(timeout=timeout))
                else:
                    cr.send(fut)
            except StopIteration:
                pass
        else:
            if isinstance(fut, FutureArrayProtocol):
                return cr, fut
            else:
                # data is not async
                try:
                    cr.send(fut)
                except StopIteration:
                    pass
    return start
