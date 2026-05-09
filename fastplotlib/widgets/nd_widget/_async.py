import asyncio
from concurrent.futures import Executor, ThreadPoolExecutor
from typing import Any, Callable, Coroutine


async def run_in_thread_pool(
    executor: Executor, fn: Callable, *args, **kwargs
) -> Any:
    """Submit ``fn(*args, **kwargs)`` to ``executor`` and await the result."""
    return await asyncio.wrap_future(executor.submit(fn, *args, **kwargs))


def run_sync(coro: Coroutine) -> Any:
    """
    Drive an ``async def`` coroutine to completion synchronously, in a helper thread.

    Used by construction-time call sites (NDGraphic.__init__, data setter, property
    setters) that cannot be made async without coloring the public API.
    ``asyncio.run`` is dispatched to a helper thread so this never collides with a
    loop already running on the calling thread (the rendercanvas loop, Jupyter, IDEs).
    """
    with ThreadPoolExecutor(max_workers=1) as ex:
        return ex.submit(asyncio.run, coro).result()
