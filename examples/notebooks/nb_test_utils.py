from typing import *
import os
from pathlib import Path

import imageio.v3 as iio
import numpy as np

from fastplotlib import Plot, GridPlot

# make dirs for screenshots and diffs
current_dir = Path(__file__).parent

SCREENSHOTS_DIR = current_dir.joinpath("screenshots")
DIFFS_DIR = current_dir.joinpath("diffs")

os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
os.makedirs(DIFFS_DIR, exist_ok=True)


# store all the failures to allow the nb to proceed to test other examples
FAILURES = list()


def _run_tests():
    if "FASTPLOTLIB_NB_TESTS" not in os.environ.keys():
        return False

    if os.environ["FASTPLOTLIB_NB_TESTS"] == "1":
        return True

    return False


def plot_test(name, plot: Union[Plot, GridPlot]):
    if not _run_tests():
        return
    snapshot = plot.canvas.snapshot()

    if "REGENERATE_SCREENSHOTS" in os.environ.keys():
        if os.environ["REGENERATE_SCREENSHOTS"] == "1":
            regenerate_screenshot(name, snapshot.data)

    try:
        assert_screenshot_equal(name, snapshot.data)
    except AssertionError:
        FAILURES.append(name)


def regenerate_screenshot(name, data):
        iio.imwrite(SCREENSHOTS_DIR.joinpath(f"nb-{name}.png"), data)


def assert_screenshot_equal(name, data):
    ground_truth = iio.imread(SCREENSHOTS_DIR.joinpath(f"nb-{name}.png"))

    is_similar = np.allclose(data, ground_truth)

    update_diffs(name, is_similar, data, ground_truth)

    assert is_similar, (
        f"notebook snapshot for {name} has changed"
    )


def update_diffs(name, is_similar, img, ground_truth):
    diffs_rgba = None

    def get_diffs_rgba(slicer):
        # lazily get and cache the diff computation
        nonlocal diffs_rgba
        if diffs_rgba is None:
            # cast to float32 to avoid overflow
            # compute absolute per-pixel difference
            diffs_rgba = np.abs(ground_truth.astype("f4") - img)
            # magnify small values, making it easier to spot small errors
            diffs_rgba = ((diffs_rgba / 255) ** 0.25) * 255
            # cast back to uint8
            diffs_rgba = diffs_rgba.astype("u1")
        return diffs_rgba[..., slicer]

    # split into an rgb and an alpha diff
    diffs = {
        DIFFS_DIR.joinpath(f"nb-diff-{name}-rgb.png"): slice(0, 3),
        DIFFS_DIR.joinpath(f"nb-diff-{name}-alpha.png"): 3,
    }

    for path, slicer in diffs.items():
        if not is_similar:
            diff = get_diffs_rgba(slicer)
            iio.imwrite(path, diff)
        elif path.exists():
            path.unlink()


def notebook_finished():
    if not _run_tests():
        return

    if len(FAILURES) > 0:
        raise AssertionError(
            f"Failures for plots:\n{FAILURES}"
        )
