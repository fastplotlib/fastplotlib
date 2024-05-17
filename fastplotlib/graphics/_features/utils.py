import pygfx
import numpy as np
from typing import Iterable


def parse_colors(
    colors: str | np.ndarray | Iterable[str],
    n_colors: int | None,
    alpha: float | None = None,
    key: int | tuple | slice | None = None,
):
    """

    Parameters
    ----------
    colors
    n_colors
    alpha
    key

    Returns
    -------

    """
