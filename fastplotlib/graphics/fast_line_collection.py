from typing import *
from copy import deepcopy
import weakref

import numpy as np
import pygfx

from ._base import Interaction, PreviouslyModifiedData, GraphicCollection, Graphic
from .line import LineGraphic
from .selectors import LinearRegionSelector, LinearSelector
from ..utils import make_colors, make_pygfx_colors
from .features import PointsDataFeature, ColorFeature


def parse_colors(colors, n_colors, alpha = 1.0):
    # if provided as a numpy array of str
    if isinstance(colors, np.ndarray):
        if colors.dtype.kind in ["U", "S"]:
            colors = colors.tolist()
    # if the color is provided as a numpy array
    if isinstance(colors, np.ndarray):
        if colors.shape == (4,):  # single RGBA array
            data = np.repeat(
                np.array([colors]),
                n_colors,
                axis=0
            )
        # else assume it's already a stack of RGBA arrays, keep this directly as the data
        elif colors.ndim == 2:
            if colors.shape[1] != 4 and colors.shape[0] != n_colors:
                raise ValueError(
                    "Valid array color arguments must be a single RGBA array or a stack of "
                    "RGBA arrays for each datapoint in the shape [n_datapoints, 4]"
                )
            data = colors
        else:
            raise ValueError(
                "Valid array color arguments must be a single RGBA array or a stack of "
                "RGBA arrays for each datapoint in the shape [n_datapoints, 4]"
            )

    # if the color is provided as an iterable
    elif isinstance(colors, (list, tuple, np.ndarray)):
        # if iterable of str
        if all([isinstance(val, str) for val in colors]):
            if not len(colors) == n_colors:
                raise ValueError(
                    f"Valid iterable color arguments must be a `tuple` or `list` of `str` "
                    f"where the length of the iterable is the same as the number of datapoints."
                )

            data = np.vstack([np.array(pygfx.Color(c)) for c in colors])

        # if it's a single RGBA array as a tuple/list
        elif len(colors) == 4:
            c = pygfx.Color(colors)
            data = np.repeat(np.array([c]), n_colors, axis=0)

        else:
            raise ValueError(
                f"Valid iterable color arguments must be a `tuple` or `list` representing RGBA values or "
                f"an iterable of `str` with the same length as the number of datapoints."
            )
    elif isinstance(colors, str):
        if colors == "random":
            data = np.random.rand(n_colors, 4)
            data[:, -1] = alpha
        else:
            data = make_pygfx_colors(colors, n_colors)
    else:
        # assume it's a single color, use pygfx.Color to parse it
        data = make_pygfx_colors(colors, n_colors)

    if alpha != 1.0:
        data[:, -1] = alpha

    return data


def parse_data(data):
    if data.ndim == 1:
        data = np.dstack([np.arange(data.size, dtype=data.dtype), data])[0]

    if data.shape[1] != 3:
        if data.shape[1] != 2:
            raise ValueError(f"Must pass 1D, 2D or 3D data to")

        # zeros for z
        zs = np.zeros(data.shape[0], dtype=data.dtype)

        data = np.dstack([data[:, 0], data[:, 1], zs])[0]

    return data


# we use interactive features setters from LineGraphic but we don't instantiate the world object etc.
class PseudoLine(LineGraphic):
    def __init__(
            self,
            data,
            colors,
            collection_index: int,
            buffer_sub_range,
            name: str = None
    ):
        self.collection_index = collection_index

        self.data = PointsDataFeature(self, data, collection_index=collection_index, sub_range=buffer_sub_range)

        # if cmap is not None:
        #     colors = make_colors(n_colors=self.data().shape[0], cmap=cmap, alpha=alpha)

        self.colors = ColorFeature(
            self,
            colors,
            n_colors=self.data().shape[0],
            alpha=1.0,
            collection_index=collection_index,
            sub_range=buffer_sub_range
        )


class FastLineCollection(Graphic):
    feature_events = (
        "data",
        "colors",
        "cmap",
        "thickness",
        "present"
    )

    def __init__(
            self,
            data: List[np.ndarray],
            z_position: Union[List[float], float] = None,
            thickness: Union[float, List[float]] = 2.0,
            colors: Union[List[np.ndarray], np.ndarray] = "w",
            alpha: float = 1.0,
            cmap: Union[List[str], str] = None,
            *args,
            **kwargs
    ):
        """
        Uses a single LineGraphic to behave like a collection
        """

        data_stack = parse_data(np.vstack(data).astype(np.float32))

        self.graphics = list()

        zero_alpha_ixs = list()

        colors_list = list()

        # color for this line segment
        if colors == "random":
            for single_line_data in data:
                # make a random color for this segment
                c = np.random.rand(4)
                c[-1] = alpha
                # this will generate repeats so that it has the same number of colors as the geometry positions
                # for each datapoint
                c = parse_colors(c, single_line_data.shape[0], alpha=alpha).astype(np.float32)
                colors_list.append(c)

            colors_array = np.vstack(colors_list).astype(np.float32)

        else:
            colors_array = parse_colors(colors, data_stack.shape[0], alpha=alpha).astype(np.float32)

        # get the start and end indices of each line segment
        start_offset = 0
        for i, single_line_data in enumerate(data):
            # sub buffer range
            # skip first and last index because it joins between segments
            sub_range = (start_offset + 1, start_offset + single_line_data.shape[0] - 1)

            pseudo_line = PseudoLine(
                data=data_stack[slice(*sub_range)],
                colors=colors_array[slice(*sub_range)],
                collection_index=i,
                buffer_sub_range=sub_range
            )
            self.graphics.append(pseudo_line)

            start_offset += single_line_data.shape[0]
            zero_alpha_ixs += [start_offset - 1, start_offset]

        # set the alpha of in-between points to zero
        zero_alpha_ixs = np.array(zero_alpha_ixs[:-1])

        colors_array[zero_alpha_ixs, -1] = 0

        super(FastLineCollection, self).__init__(*args, *kwargs)

        if thickness < 1.1:
            material = pygfx.LineThinMaterial
        else:
            material = pygfx.LineMaterial

        world_object: pygfx.Line = pygfx.Line(
            # self.data.feature_data because data is a Buffer
            geometry=pygfx.Geometry(positions=data_stack, colors=colors_array),
            material=material(thickness=thickness, vertex_colors=True)
        )

        if z_position is not None:
            self.position_z = z_position

        self._set_world_object(world_object)
        for g in self.graphics:
            g.loc = self.loc
