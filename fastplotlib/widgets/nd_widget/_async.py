import asyncio
from concurrent.futures import Executor, Future, ThreadPoolExecutor
from typing import Any, Callable, Coroutine

from rendercanvas.utils.asyncs import Event, detect_current_call_soon_threadsafe


async def wait_for_future(future: Future) -> Any:
    """
    Await a ``concurrent.futures.Future`` from any rendercanvas-supported async
    backend (asyncio for glfw/jupyter, the rendercanvas asyncadapter for qt/wx).

    ``asyncio.wrap_future`` cannot be used because the asyncadapter only
    understands its own awaitables (see rendercanvas docs: "restrict your use
    of async features to ``sleep`` and ``Event``"). We instead build the same
    primitive on top of rendercanvas's cross-framework :class:`Event`,
    signaled via the active loop's ``call_soon_threadsafe`` so the future's
    done-callback (which runs on the executor thread) hands control back to
    the event loop safely.
    """
    event = Event()
    call_soon_threadsafe = detect_current_call_soon_threadsafe()
    future.add_done_callback(lambda f: call_soon_threadsafe(event.set))
    await event.wait()
    return future.result()


async def run_in_thread_pool(
    executor: Executor, fn: Callable, *args, **kwargs
) -> Any:
    """Submit ``fn(*args, **kwargs)`` to ``executor`` and await the result."""
    return await wait_for_future(executor.submit(fn, *args, **kwargs))


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
