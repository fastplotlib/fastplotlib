"""
Test suite utilities.
"""

from pathlib import Path
import subprocess
import sys
from itertools import chain

import numpy as np


ROOT = Path(__file__).parents[2]  # repo root
examples_dir = ROOT / "examples"
screenshots_dir = examples_dir / "screenshots"
diffs_dir = examples_dir / "diffs"

# examples live in themed sub-folders
example_globs = [
    "image/*.py",
    "image_widget/*.py",
    "heatmap/*.py",
    "scatter/*.py",
    "line/*.py",
    "line_collection/*.py",
    "gridplot/*.py",
    "flex_layouts/*.py"
    "misc/*.py",
    "selection_tools/*.py",
    "guis/*.py",
]


def get_wgpu_backend():
    """
    Query the configured wgpu backend driver.
    """
    code = "import wgpu.utils; info = wgpu.utils.get_default_device().adapter.info; print(info['adapter_type'], info['backend_type'])"
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            code,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        cwd=ROOT,
    )
    out = result.stdout.strip()
    err = result.stderr.strip()
    return err if "traceback" in err.lower() else out


wgpu_backend = get_wgpu_backend()
is_lavapipe = wgpu_backend.lower() == "cpu vulkan"


def find_examples(query=None, negative_query=None, return_stems=False):
    """Finds all modules to be tested."""
    result = []
    for example_path in chain(*(examples_dir.glob(x) for x in example_globs)):
        example_code = example_path.read_text(encoding="UTF-8")
        query_match = query is None or query in example_code
        negative_query_match = (
            negative_query is None or negative_query not in example_code
        )
        if query_match and negative_query_match:
            result.append(example_path)
    result = list(sorted(result))
    if return_stems:
        result = [r.stem for r in result]
    return result


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


def prep_for_write(img):
    """Convert 0..1 float back to 0..255 uint8."""
    assert len(img.shape) == 3
    assert np.min(img) >= 0 and np.max(img) <= 1
    if img.dtype != "u1":
        img = np.round(img * 255).astype("u1")
    return img


def rescale_arr(arr, min, max):
    """
    histogram rescale utility function
    e.g. if the values are 0.3..0.7
    they are rescaled to min..max
    """
    return np.interp(arr, (arr.min(), arr.max()), (min, max))


def rgb_to_hls(rgb):
    """
    convert rgb to hls
    assumes input ranges are 0..1
    returns values in range 0..1

    vectorized version of colorsys.rgb_to_hls
    """
    maxc = np.max(rgb, axis=-1)
    minc = np.min(rgb, axis=-1)
    hls = np.empty_like(rgb)
    l = (minc + maxc) / 2.0  # noqa: E741

    with np.errstate(invalid="ignore"):
        mask = l <= 0.5
        idx = np.where(mask)
        hls[(*idx, 2)] = (maxc[idx] - minc[idx]) / (maxc[idx] + minc[idx])

        idx = np.where(~mask)
        hls[(*idx, 2)] = (maxc[idx] - minc[idx]) / (2.0 - maxc[idx] - minc[idx])

        maxc_minc = maxc - minc
        rc = (maxc - rgb[..., 0]) / maxc_minc
        gc = (maxc - rgb[..., 1]) / maxc_minc
        bc = (maxc - rgb[..., 2]) / maxc_minc

    mask1 = rgb[..., 0] == maxc
    idx = np.where(mask1)
    hls[(*idx, 0)] = bc[idx] - gc[idx]

    mask2 = rgb[..., 1] == maxc
    idx = np.where(~mask1 & mask2)
    hls[(*idx, 0)] = 2.0 + rc[idx] - bc[idx]

    idx = np.where(~mask1 & ~mask2)
    hls[(*idx, 0)] = 4.0 + gc[idx] - rc[idx]

    hls[..., 0] = (hls[..., 0] / 6.0) % 1.0

    idx = np.where(minc == maxc)
    hls[idx] = 0.0
    hls[..., 1] = l

    return hls


def hls_to_rgb(hls):
    """
    convert hls to rgb
    assumes input ranges are 0..1
    returns values in range 0..1

    vectorized version of colorsys.hls_to_rgb
    """
    rgb = np.empty_like(hls)

    m2 = np.empty_like(hls[..., 1])
    mask = hls[..., 1] <= 0.5
    idx = np.where(mask)
    m2[idx] = hls[(*idx, 1)] * (1.0 + hls[(*idx, 2)])
    idx = np.where(~mask)
    m2[idx] = hls[(*idx, 1)] + hls[(*idx, 2)] - (hls[(*idx, 1)] * hls[(*idx, 2)])
    m1 = 2.0 * hls[..., 1] - m2

    h1 = (hls[..., 0] + 1 / 3) % 1.0
    h2 = hls[..., 0] % 1.0
    h3 = (hls[..., 0] - 1 / 3) % 1.0

    for i, h in enumerate([h1, h2, h3]):
        mask1 = h < 1 / 6
        idx = np.where(mask1)
        rgb[(*idx, i)] = m1[idx] + (m2[idx] - m1[idx]) * h[idx] * 6.0

        mask2 = h < 0.5
        idx = np.where(~mask1 & mask2)
        rgb[(*idx, i)] = m2[idx]

        mask3 = h < 2 / 3
        idx = np.where(~mask1 & ~mask2 & mask3)
        rgb[(*idx, i)] = m1[idx] + (m2[idx] - m1[idx]) * ((2 / 3) - h[idx]) * 6.0

        idx = np.where(~mask1 & ~mask2 & ~mask3)
        rgb[(*idx, i)] = m1[idx]

    return rgb


def generate_diff(src, target, fuzz=0.05):
    """
    Generate an image that
    highlights the differences between src and target image
    any pixels with a euclidian color distance < fuzz will be ignored
    fuzz is expressed as a percentage of the maximum possible distance
    which is the distance between (0,0,0) and (1,1,1) = sqrt(3).
    """
    # compute euclidian distance between pixels
    # and normalize to 0..1
    max_dist = np.linalg.norm([1, 1, 1], axis=-1)
    error = np.linalg.norm(np.abs(target - src), axis=-1) / max_dist
    # apply fuzz
    error_idx = np.where(error > fuzz)

    diff_img_hls = rgb_to_hls(target)
    # lighten the whole image
    diff_img_hls[..., 1] = rescale_arr(diff_img_hls[..., 1], 0.25, 1.0)
    diff_img_hls[..., 1] **= 0.2
    # reduce the color saturation
    diff_img_hls[..., 2] = rescale_arr(diff_img_hls[..., 2], 0.0, 0.75)
    diff_img_hls[..., 2] **= 2

    # make the diff pixels red
    diff_img_hls[(*error_idx, 0)] = 0
    # give them the same lighting level
    diff_img_hls[(*error_idx, 1)] = 0.5
    # saturate based on the error
    diff_img_hls[(*error_idx, 2)] = 0.5 + error[error_idx] * 0.5

    # convert back to rgb
    diff_img = hls_to_rgb(diff_img_hls)

    return diff_img
