"""
Explore Covariance Matrix
=========================

Example showing how you can explore a covariance matrix with a selector tool.
"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'animate 10s'


import fastplotlib as fpl
from sklearn import datasets
from sklearn.preprocessing import StandardScaler

# load faces dataset
faces = datasets.fetch_olivetti_faces()
data = faces["data"]

# sort the data so it's easier to understand the covariance matrix
targets = faces["target"]
sort_indices = targets.argsort()
targets_sorted = targets[sort_indices]

X = data[sort_indices]

# scale the data w.r.t. mean and standard deviation
X = StandardScaler().fit_transform(X)

# compute covariance matrix
X = X.T
cov = X @ X.T / X.shape[1]

# reshaped image for each sample wil be 64 x 64 pixels
img = cov[0].reshape(64, 64)

# figure kwargs for image widget
# controller_ids = [[0, 1]] so we get independent controllers for each supblot
# the covariance matrix is 4096 x 4096 and the reshaped image ix 64 x 64
figure_kwargs = {"size": (700, 400), "controller_ids": [[0, 1]]}

# create image widget
iw = fpl.ImageWidget(
    data=[cov, img],  # display the covariance matrix and reshaped image of a row
    cmap="bwr",  # diverging colormap
    names=["covariance", "row image"],
    figure_kwargs=figure_kwargs,
)

# graphic that corresponds to image widget data array 0
# 0 is the covariance matrix, 1 is the reshaped image of a row from the covariance matrix

# add a linear selector to select y axis values so we can select rows of the cov matrix
selector_cov = iw.managed_graphics[0].add_linear_selector(axis="y")

# if you are exploring other types of matrices which are not-symmetric
# you can also add a column selector by setting axis="x"

# set vmin vmax
for g in iw.managed_graphics:
    g.vmin, g.vmax = -1, 1


# event handler when the covariance matrix row changes
@selector_cov.add_event_handler("selection")
def update_img(ev):
    # get the row index
    ix = ev.get_selected_index()

    # get the image the corresponds to this row
    img = cov[ix].reshape(64, 64)

    # change the reshaped image graphic data
    iw.managed_graphics[1].data = img


figure = iw.figure  # not required, just for the docs gallery to pick it up


# move the selector programmatically, this is mainly for the docs gallery
# for real use you can interact with the selector with your mouse
def animate():
    selector_cov.selection += 1


iw.figure.add_animations(animate)

iw.show()

# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
