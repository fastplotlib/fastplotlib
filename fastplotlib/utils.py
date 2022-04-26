import numpy as np
from matplotlib import cm
from pygfx import Texture


def get_cmap(name: str) -> Texture:
    cmap = np.vstack([getattr(cm, name)(i) for i in range(256)])[:, 0:-1].astype(np.float32)
    return Texture(cmap, dim=1).get_view()
