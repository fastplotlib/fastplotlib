from warnings import warn
from typing import Any, Literal

import numpy as np
from numpy.typing import NDArray

from wgpu.gui.base import log_exception

import pygfx


def to_gpu_supported_dtype(array):
    """
    convert input array to float32 numpy array
    """
    if isinstance(array, np.ndarray):
        if not array.dtype == np.float32:
            warn(f"casting {array.dtype} array to float32")
            return array.astype(np.float32)
        return array

    # try to make a numpy array from it, should not copy, tested with jax arrays
    return np.asarray(array).astype(np.float32)


class FeatureEvent(pygfx.Event):
    """
    **All event instances have the following attributes**

    +------------+-------------+-----------------------------------------------+
    | attribute  | type        | description                                   |
    +============+=============+===============================================+
    | type       | str         | "colors" - name of the event                  |
    +------------+-------------+-----------------------------------------------+
    | graphic    | Graphic     | graphic instance that the event is from       |
    +------------+-------------+-----------------------------------------------+
    | info       | dict        | event info dictionary (see below)             |
    +------------+-------------+-----------------------------------------------+
    | target     | WorldObject | pygfx rendering engine object for the graphic |
    +------------+-------------+-----------------------------------------------+
    | time_stamp | float       | time when the event occured, in ms            |
    +------------+-------------+-----------------------------------------------+

    """

    def __init__(self, type: str, info: dict):
        super().__init__(type=type)
        self.info = info


class GraphicFeature:
    def __init__(self, **kwargs):
        self._event_handlers = list()
        self._block_events = False

        # used by @block_reentrance decorator to block re-entrance into set_value functions
        self._reentrant_block: bool = False

    @property
    def value(self) -> Any:
        """Graphic Feature value, must be implemented in subclass"""
        raise NotImplemented

    def set_value(self, graphic, value: float):
        """Graphic Feature value setter, must be implemented in subclass"""
        raise NotImplementedError

    def block_events(self, val: bool):
        """
        Block all events from this feature

        Parameters
        ----------
        val: bool
            ``True`` or ``False``

        """
        self._block_events = val

    def add_event_handler(self, handler: callable):
        """
        Add an event handler. All added event handlers are called when this feature changes.

        Used by `Graphic` classes to add to their event handlers, not meant for users. Users
        add handlers to Graphic instances only.

        The ``handler`` must accept a :class:`.FeatureEvent` as the first and only argument.

        Parameters
        ----------
        handler: callable
            a function to call when this feature changes

        """
        if not callable(handler):
            raise TypeError("event handler must be callable")

        if handler in self._event_handlers:
            warn(f"Event handler {handler} is already registered.")
            return

        self._event_handlers.append(handler)

    def remove_event_handler(self, handler: callable):
        """
        Remove a registered event ``handler``.

        Parameters
        ----------
        handler: callable
            event handler to remove

        """
        if handler not in self._event_handlers:
            raise KeyError(f"event handler {handler} not registered.")

        self._event_handlers.remove(handler)

    def clear_event_handlers(self):
        """Clear all event handlers"""
        self._event_handlers.clear()

    def _call_event_handlers(self, event_data: FeatureEvent):
        if self._block_events:
            return

        for func in self._event_handlers:
            with log_exception(
                f"Error during handling {self.__class__.__name__} event"
            ):
                func(event_data)


class BufferManager(GraphicFeature):
    """Smaller wrapper for pygfx.Buffer"""

    def __init__(
        self,
        data: NDArray | pygfx.Buffer,
        buffer_type: Literal["buffer", "texture", "texture-array"] = "buffer",
        isolated_buffer: bool = True,
        texture_dim: int = 2,
        **kwargs,
    ):
        super().__init__()
        if isolated_buffer and not isinstance(data, pygfx.Resource):
            # useful if data is read-only, example: memmaps
            bdata = np.zeros(data.shape, dtype=data.dtype)
            bdata[:] = data[:]
        else:
            # user's input array is used as the buffer
            bdata = data

        if isinstance(data, pygfx.Resource):
            # already a buffer, probably used for
            # managing another BufferManager, example: VertexCmap manages VertexColors
            self._buffer = data
        elif buffer_type == "buffer":
            self._buffer = pygfx.Buffer(bdata)
        elif buffer_type == "texture":
            # TODO: placeholder, not currently used since TextureArray is used specifically for Image graphics
            self._buffer = pygfx.Texture(bdata, dim=texture_dim)
        else:
            raise ValueError(
                "`data` must be a pygfx.Buffer instance or `buffer_type` must be one of: 'buffer' or 'texture'"
            )

        self._event_handlers: list[callable] = list()

        self._shared: int = 0

    @property
    def value(self) -> np.ndarray:
        """numpy array object representing the data managed by this buffer"""
        return self.buffer.data

    def set_value(self, graphic, value):
        """Sets values on entire array"""
        self[:] = value

    @property
    def buffer(self) -> pygfx.Buffer | pygfx.Texture:
        """managed buffer"""
        return self._buffer

    @property
    def shared(self) -> int:
        """Number of graphics that share this buffer"""
        return self._shared

    @property
    def __array_interface__(self):
        raise BufferError(
            f"Cannot use graphic feature buffer as an array, use <feature-name>.value instead.\n"
            f"Examples: line.data.value, line.colors.value, scatter.data.value, scatter.sizes.value"
        )

    def __getitem__(self, item):
        return self.buffer.data[item]

    def __setitem__(self, key, value):
        raise NotImplementedError

    def _parse_offset_size(
        self,
        key: int | slice | np.ndarray[int | bool] | list[bool | int],
        upper_bound: int,
    ):
        """
        parse offset and size for first, i.e. n_datapoints, dimension
        """
        if np.issubdtype(type(key), np.integer):
            # simplest case, just an int
            offset = key
            size = 1

        elif isinstance(key, slice):
            # TODO: off-by-one sometimes when step is used
            #  the offset can be one to the left or the size
            #  is one extra so it's not really an issue for now
            # parse slice
            start, stop, step = key.indices(upper_bound)

            # account for backwards indexing
            if (start > stop) and step < 0:
                offset = stop
            else:
                offset = start

            # slice.indices will give -1 if None is passed
            # which just means 0 here since buffers do not
            # use negative indexing
            offset = max(0, offset)

            # number of elements to upload
            # this is indexing so do not add 1
            size = abs(stop - start)

        elif isinstance(key, (np.ndarray, list)):
            if isinstance(key, list):
                # convert to array
                key = np.array(key)

            if not key.ndim == 1:
                raise TypeError(
                    f"can only use 1D arrays for fancy indexing, you have passed a data with: {key.ndim} dimensions"
                )

            if key.dtype == bool:
                # convert bool mask to integer indices
                key = np.nonzero(key)[0]

            if not np.issubdtype(key.dtype, np.integer):
                # fancy indexing doesn't make sense with non-integer types
                raise TypeError(
                    f"can only using integer or booleans arrays for fancy indexing, your array is of type: {key.dtype}"
                )

            if key.size < 1:
                # nothing to update
                return

            # convert any negative integer indices to positive indices
            key %= upper_bound

            # index of first element to upload
            offset = key.min()

            # size range to upload
            # add 1 because this is direct
            # passing of indices, not a start:stop
            size = np.ptp(key) + 1

        else:
            raise TypeError(
                f"invalid key for indexing buffer: {key}\n"
                f"valid ways to index buffers are using integers, slices, or fancy indexing with integers or bool"
            )

        return offset, size

    def _update_range(
        self,
        key: (
            int | slice | np.ndarray[int | bool] | list[bool | int] | tuple[slice, ...]
        ),
    ):
        """
        Uses key from slicing to determine the offset and
        size of the buffer to mark for upload to the GPU
        """
        upper_bound = self.value.shape[0]

        if isinstance(key, tuple):
            if any([k is Ellipsis for k in key]):
                # let's worry about ellipsis later
                raise TypeError("ellipses not supported for indexing buffers")
            # if multiple dims are sliced, we only need the key for
            # the first dimension corresponding to n_datapoints
            key: int | np.ndarray[int | bool] | slice = key[0]

        offset, size = self._parse_offset_size(key, upper_bound)
        self.buffer.update_range(offset=offset, size=size)

    def _emit_event(self, type: str, key, value):
        if len(self._event_handlers) < 1:
            return

        event_info = {
            "key": key,
            "value": value,
        }
        event = FeatureEvent(type, info=event_info)

        self._call_event_handlers(event)

    def __len__(self):
        raise NotImplementedError

    def __repr__(self):
        return f"{self.__class__.__name__} buffer data:\n" f"{self.value.__repr__()}"


def block_reentrance(set_value):
    # decorator to block re-entrant set_value methods
    # useful when creating complex, circular, bidirectional event graphs
    def set_value_wrapper(self: GraphicFeature, graphic_or_key, value):
        """
        wraps GraphicFeature.set_value

        self: GraphicFeature instance

        graphic_or_key: graphic, or key if a BufferManager

        value: the value passed to set_value()
        """
        # set_value is already in the middle of an execution, block re-entrance
        if self._reentrant_block:
            return
        try:
            # block re-execution of set_value until it has *fully* finished executing
            self._reentrant_block = True
            set_value(self, graphic_or_key, value)
        except Exception as exc:
            # raise original exception
            raise exc  # set_value has raised. The line above and the lines 2+ steps below are probably more relevant!
        finally:
            # set_value has finished executing, now allow future executions
            self._reentrant_block = False

    return set_value_wrapper
