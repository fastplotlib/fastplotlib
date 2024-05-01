from typing import *
import os
from pathlib import Path

import imageio.v3 as iio
import numpy as np

import fastplotlib as fpl

# make dirs for screenshots and diffs
current_dir = Path(__file__).parent

SCREENSHOTS_DIR = current_dir.joinpath("screenshots")
DIFFS_DIR = current_dir.joinpath("diffs")

os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
os.makedirs(DIFFS_DIR, exist_ok=True)

TOLERANCE = 0.025

# store all the failures to allow the nb to proceed to test other examples
FAILURES = list()

if "FASTPLOTLIB_NB_TESTS" not in os.environ.keys():
    TESTING = False

else:
    if os.environ["FASTPLOTLIB_NB_TESTS"] == "1":
        TESTING = True


# TODO: consolidate testing functions into one module so we don't have this separate one for notebooks

def rgba_to_rgb(img: np.ndarray) -> np.ndarray:
    black = np.zeros(img.shape).astype(np.uint8)
    black[:, :, -1] = 255

    img_alpha = img[..., -1] / 255

    rgb = img[..., :-1] * img_alpha[..., None] + black[..., :-1] * np.ones(
        img_alpha.shape
    )[..., None] * (1 - img_alpha[..., None])

    return rgb.round().astype(np.uint8)


# image comparison functions from: https://github.com/pygfx/image-comparison
def image_similarity(src, target, threshold=0.2):
    """Compute normalized RMSE 0..1 and decide if similar based on threshold.

    For every pixel, the euclidian distance between RGB values is computed,
    and normalized by the maximum possible distance (between black and white).
    The RMSE is then computed from those errors.

    The normalized RMSE is used to compute the
    similarity metric, so larger errors (euclidian distance
    between two RGB colors) will have a disproportionately
    larger effect on the score than smaller errors.

    In other words, lots of small errors will lead to a good score
    (closer to 0) whereas a few large errors will lead to a bad score
    (closer to 1).
    """
    float_type = np.float64
    src = np.asarray(src, dtype=float_type)
    target = np.asarray(target, dtype=float_type)
    denom = np.sqrt(np.mean(src * src))
    mse = np.mean((src - target) ** 2)
    rmse = np.sqrt(mse) / denom

    similar = bool(rmse < threshold)
    return similar, rmse


def normalize_image(img):
    """Discard the alpha channel and convert from 0..255 uint8 to 0..1 float."""
    assert len(img.shape) == 3

    # normalize to 0..1 range
    if img.dtype == "u1" or np.max(img) > 1:
        img = img / 255
        assert np.min(img) >= 0 and np.max(img) <= 1

    # discard alpha channel
    # unsupported if it's not fully opaque
    if img.shape[-1] == 4:
        assert np.max(img[..., 3]) == 1
        img = img[..., :-1]

    return img


def plot_test(name, fig: fpl.Figure):
    if not TESTING:
        return

    snapshot = fig.canvas.snapshot()
    rgb_img = rgba_to_rgb(snapshot.data)

    if "REGENERATE_SCREENSHOTS" in os.environ.keys():
        if os.environ["REGENERATE_SCREENSHOTS"] == "1":
            regenerate_screenshot(name, rgb_img)

    assert_screenshot_equal(name, rgb_img)


def regenerate_screenshot(name, data):
        iio.imwrite(SCREENSHOTS_DIR.joinpath(f"nb-{name}.png"), data)


def assert_screenshot_equal(name, data):
    ground_truth = iio.imread(SCREENSHOTS_DIR.joinpath(f"nb-{name}.png"))

    img = normalize_image(data)
    ref_img = normalize_image(ground_truth)

    similar, rmse = image_similarity(img, ref_img, threshold=TOLERANCE)

    update_diffs(name, similar, data, ground_truth)

    if not similar:
        FAILURES.append(
            (name, rmse)
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
    }

    for path, slicer in diffs.items():
        if not is_similar:
            diff = get_diffs_rgba(slicer)
            iio.imwrite(path, diff)
        elif path.exists():
            path.unlink()


def notebook_finished():
    if not TESTING:
        return

    if len(FAILURES) > 0:
        raise AssertionError(
            f"Failures for plots:\n{FAILURES}"
        )
