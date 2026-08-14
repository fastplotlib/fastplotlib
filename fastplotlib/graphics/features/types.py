import numpy as np
import pygfx

RGB = tuple[float, float, float] | tuple[int, int, int] | list[int] | list[float]
RGBA = tuple[float, float, float, float] | tuple[int, int, int, int] | list[int] | list[float] | pygfx.Color

ArrayRGBA = np.ndarray[tuple[int, int, int] | tuple[int, int, int, int], np.dtype[np.number]]

ColorLike = RGB | RGBA | ArrayRGBA | pygfx.Color | str

# [n, 3 | 4] RGBA array
MultiColorArray = np.ndarray[tuple[int, int], np.dtype[np.number]]

MultiColorLike = tuple[ColorLike] | list[ColorLike] | MultiColorArray
