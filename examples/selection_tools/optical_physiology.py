import numpy as np
import fastplotlib as fpl
from sklearn.decomposition import FastICA
from scipy.spatial import ConvexHull


def generate_time(
        n_timepoints: int,
        n_components: int,
        firing_prop = 0.05,
) -> np.ndarray:
    """
    Generate some time series data using an AR process:

    x_(t+1) = a * x_t

    One distinct time series component is generated per row.

    Parameters
    ----------
    n_timepoints: int

    n_components: int

    noise_sigma: float
        add random gaussian noise with this sigma value

    firing_prop: float

    Returns
    -------
    np.ndarray, np.ndarray
        data [n_components, n_timepoints]

    """

    x = np.zeros((n_components, n_timepoints)) + 0.01

    a = 0.7

    spikes = list()

    for i in range(n_components):
        spikes.append((np.random.rand(n_timepoints) < firing_prop).astype(bool))

    for c_ix in range(n_components):
        for i in range(1, n_timepoints):
            x[c_ix, i] = (a * x[c_ix, i - 1]) + (1 * spikes[c_ix][i])

    return x


def gaussian_2d(x=0, y=0, mx=0, my=0, sx=1, sy=1):
    """generate a 2D gaussian kernel"""
    return 1. / (2. * np.pi * sx * sy) * np.exp(-((x - mx)**2. / (2. * sx**2.) + (y - my)**2. / (2. * sy**2.)))


def generate_movie(time_components: np.ndarray, dims: tuple[int, int] = (50, 50), noise_sigma=0.1) -> np.ndarray:
    n_timepoints, n_components = time_components.shape

    centers = np.random.rand(n_components, 2)
    centers[:, 0] *= dims[0]
    centers[:, 1] *= dims[1]
    centers = centers.clip(0, max=min(dims) - 20)
    centers = centers.astype(int)

    r = -20, 20
    r = np.linspace(*r)
    x, y = np.meshgrid(r, r)
    space_component = gaussian_2d(x, y, sx=2, sy=2)[18:-18, 18:-18]
    space_component /= space_component.max()

    space_shape = space_component.shape

    movie = np.zeros(shape=[n_components, *dims])

    for time_component, center in zip(time_components, centers):
        space_time = np.outer(space_component, time_component).reshape(*space_component.shape, time_components.shape[1]).transpose(2, 0, 1)
        row_ix, col_ix = center

        movie[:, row_ix:row_ix + space_shape[0], col_ix:col_ix + space_shape[1]] += space_time
    movie += np.random.normal(loc=0, scale=noise_sigma, size=movie.size).reshape(movie.shape)
    return movie


def decomposition(movie, n_components=5):
    n_timepoints = movie.shape[0]
    X = movie.reshape(n_timepoints, np.prod(movie.shape[1:])).T

    ica = FastICA(n_components=n_components, fun="exp", random_state=0)

    spatial_components = np.abs(ica.fit_transform(X).reshape(*dims, n_components).T)
    temporal_components = np.abs(ica.mixing_)

    contours = list()
    for index in range(n_components):
        points = np.array(np.where(spatial_components[index] > np.percentile(spatial_components[index], 98))).T
        hull = ConvexHull(points)
        vertices = np.vstack([hull.points[hull.vertices], hull.points[hull.vertices][0]])
        contours.append(vertices)

    return contours, temporal_components.T


n_components = 5
n_timepoints = 100
dims = (50, 50)

np.random.seed(0)
time_components = generate_time(
    n_timepoints=n_timepoints,
    n_components=n_components,
)

np.random.seed(10)
movie = generate_movie(time_components, dims=dims, noise_sigma=0.1)

contours, time_series = decomposition(movie, n_components=n_components)


figure = fpl.Figure(
    (3, 1),
    size=(700, 1024),
    names=["movie", "heatmap", "selected"]
)

figure["heatmap"].camera.maintain_aspect = False
figure["selected"].camera.maintain_aspect = False

movie_graphic = figure["movie"].add_image(movie[0], cmap="viridis")
contours_graphic = figure["movie"].add_line_collection(contours, cmap="tab10")

heatmap_graphic = figure["heatmap"].add_image(time_series, cmap="viridis")
selector_time_heatmap = heatmap_graphic.add_linear_selector()
selector_component_heatmap = heatmap_graphic.add_linear_selector(axis="y")

temporal_selected_graphic = figure["selected"].add_line(time_series[0])
selector_time_line = temporal_selected_graphic.add_linear_selector()

def set_timepoint(ev):
    timepoint = ev.info["selection"]
    movie_graphic.data[:] = movie[round(timepoint)]
    selector_time_heatmap.selection = timepoint
    selector_time_line.selection = timepoint


@movie_graphic.add_event_handler("click")
def image_clicked(ev):
    contours_graphic.cmap = "tab10"
    nearest_contour = fpl.utils.get_nearest_graphics((ev.x, ev.y), contours_graphic)[0]
    nearest_contour.colors = "w"


@selector_component_heatmap.add_event_handler("selection")
def heatmap_component_changed(ev):
    index = ev.get_selected_index()
    contours_graphic.cmap = "tab10"
    contours_graphic.graphics[index].colors = "w"


figure.show()
fpl.loop.run()
