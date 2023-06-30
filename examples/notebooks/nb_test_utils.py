import os

import imageio as iio

from fastplotlib.layouts._base import PlotArea


def test_plot(name, plot: PlotArea):
    if os.environ["REGENERATE_SCREENSHOTS"] == "1":
        snapshot = plot.canvas.snapshot()
        regenerate_screenshot(snapshot.data)
        
    assert_screenshot_equal(name, snapshot.data)


def regenerate_screenshot(name, data):
    pass


def assert_screenshot_equal(name, data):
    # do stuff
    if not is_similar:
        update_screenshot_diff(name, data)


def update_screenshot_diff(name, data):
    pass
