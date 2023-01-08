import numpy as np
from matplotlib import cm


class ColormapNames:
    perceptually_uniform = ['viridis', 'plasma', 'inferno', 'magma', 'cividis']
    sequential = ['Greys', 'Purples', 'Blues', 'Greens', 'Oranges', 'Reds',
                  'YlOrBr', 'YlOrRd', 'OrRd', 'PuRd', 'RdPu', 'BuPu',
                  'GnBu', 'PuBu', 'YlGnBu', 'PuBuGn', 'BuGn', 'YlGn']

    sequential2 = ['binary', 'gist_yarg', 'gist_gray', 'gray', 'bone',
                   'pink', 'spring', 'summer', 'autumn', 'winter', 'cool',
                   'Wistia', 'hot', 'afmhot', 'gist_heat', 'copper']

    diverging = ['PiYG', 'PRGn', 'BrBG', 'PuOr', 'RdGy', 'RdBu', 'RdYlBu',
                 'RdYlGn', 'Spectral', 'coolwarm', 'bwr', 'seismic']

    cyclic = ['twilight', 'twilight_shifted', 'hsv']

    qualitative = ['Pastel1', 'Pastel2', 'Paired', 'Accent', 'Dark2',
                   'Set1', 'Set2', 'Set3', 'tab10', 'tab20', 'tab20b',
                   'tab20c']

    miscellaneous = ['flag', 'prism', 'ocean', 'gist_earth', 'terrain',
                     'gist_stern', 'gnuplot', 'gnuplot2', 'CMRmap',
                     'cubehelix', 'brg', 'gist_rainbow', 'rainbow', 'jet',
                     'turbo', 'nipy_spectral', 'gist_ncar']

    all = perceptually_uniform + sequential + sequential2 + \
          diverging + cyclic + qualitative + miscellaneous


def make_cmap(name: str, alpha: float = 1.0) -> np.ndarray:
    _cm = getattr(cm, name)

    if name in ColormapNames.qualitative:
        n_colors = getattr(_cm, "N")
    else:
        n_colors = 256

    cmap = np.vstack([_cm(i) for i in range(n_colors)])
    cmap[:, -1] = alpha

    return cmap.astype(np.float32)


if __name__ == '__main__':
    for name in ColormapNames().all:
        np.savetxt(f'./colormaps/{name}', make_cmap(name))
