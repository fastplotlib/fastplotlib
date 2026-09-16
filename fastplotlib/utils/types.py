from collections import namedtuple
from typing import Iterable

import numpy as np
from numpy._typing import NDArray

import pygfx

SelectorColorStates = namedtuple("state", ["idle", "highlight", "action"])
RGB = tuple[float, float, float] | tuple[int, int, int] | list[int] | list[float]
RGBA = (
    tuple[float, float, float, float]
    | tuple[int, int, int, int]
    | list[int]
    | list[float]
    | pygfx.Color
)

# [n, 3 | 4] RGBA array
ArrayRGBA = np.ndarray[
    tuple[int, int, int] | tuple[int, int, int, int], np.dtype[np.number]
]
ColorLike = RGB | RGBA | ArrayRGBA | pygfx.Color | str
MultiColorArray = np.ndarray[tuple[int, int], np.dtype[np.number]]
MultiColorLike = tuple[ColorLike] | list[ColorLike] | MultiColorArray

# our own ColormapLike type since if we use the cmap lib's ColormapLike it expands into a huge complex union
ColormapLike = str | Iterable[ColorLike] | MultiColorLike

TupleYUV = tuple[NDArray[np.uint8], NDArray[np.uint8], NDArray[np.uint8]]
