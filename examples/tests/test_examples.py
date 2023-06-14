"""
Test that examples run without error.
"""
import importlib
import runpy
import pytest
import os
import numpy as np
import imageio.v3 as iio

from .testutils import (
    ROOT,
    examples_dir,
    screenshots_dir,
    find_examples,
    wgpu_backend,
    is_lavapipe,
    diffs_dir
)

# run all tests unless they opt-out
examples_to_run = find_examples(negative_query="# run_example = false")

# only test output of examples that opt-in
examples_to_test = find_examples(query="# test_example = true")


@pytest.mark.parametrize("module", examples_to_run, ids=lambda x: x.stem)
def test_examples_run(module, force_offscreen):
    """Run every example marked to see if they run without error."""

    runpy.run_path(module, run_name="__main__")


@pytest.fixture
def force_offscreen():
    """Force the offscreen canvas to be selected by the auto gui module."""
    os.environ["WGPU_FORCE_OFFSCREEN"] = "true"
    try:
        yield
    finally:
        del os.environ["WGPU_FORCE_OFFSCREEN"]


def test_that_we_are_on_lavapipe():
    print(wgpu_backend)
    if os.getenv("PYGFX_EXPECT_LAVAPIPE"):
        assert is_lavapipe


@pytest.mark.parametrize("module", examples_to_test, ids=lambda x: x.stem)
def test_example_screenshots(module, force_offscreen):
    """Make sure that every example marked outputs the expected."""
    # (relative) module name from project root
    module_name = module.relative_to(ROOT/"examples").with_suffix("").as_posix().replace("/", ".")

    # import the example module
    example = importlib.import_module(module_name)

    # render a frame
    img = np.asarray(example.renderer.target.draw())

    # check if _something_ was rendered
    assert img is not None and img.size > 0

    # if screenshots dir does not exist, will create
    if not os.path.exists(screenshots_dir):
        os.mkdir(screenshots_dir)

    screenshot_path = screenshots_dir / f"{module.stem}.png"

    if "REGENERATE_SCREENSHOTS" in os.environ.keys():
        if os.environ["REGENERATE_SCREENSHOTS"] == "1":
            iio.imwrite(screenshot_path, img)
            #np.save(screenshot_path, img)

    assert (
        screenshot_path.exists()
    ), "found # test_example = true but no reference screenshot available"
    #stored_img = np.load(screenshot_path)
    stored_img = iio.imread(screenshot_path)
    is_similar = np.allclose(img, stored_img, atol=1)
    update_diffs(module.stem, is_similar, img, stored_img)
    assert is_similar, (
        f"rendered image for example {module.stem} changed, see "
        f"the {diffs_dir.relative_to(ROOT).as_posix()} folder"
        " for visual diffs (you can download this folder from"
        " CI build artifacts as well)"
    )


def update_diffs(module, is_similar, img, stored_img):
    diffs_dir.mkdir(exist_ok=True)

    diffs_rgba = None

    def get_diffs_rgba(slicer):
        # lazily get and cache the diff computation
        nonlocal diffs_rgba
        if diffs_rgba is None:
            # cast to float32 to avoid overflow
            # compute absolute per-pixel difference
            diffs_rgba = np.abs(stored_img.astype("f4") - img)
            # magnify small values, making it easier to spot small errors
            diffs_rgba = ((diffs_rgba / 255) ** 0.25) * 255
            # cast back to uint8
            diffs_rgba = diffs_rgba.astype("u1")
        return diffs_rgba[..., slicer]

    # split into an rgb and an alpha diff
    diffs = {
        diffs_dir / f"diff-{module}-rgb.png": slice(0, 3),
        diffs_dir / f"diff-{module}-alpha.png": 3,
    }

    for path, slicer in diffs.items():
        if not is_similar:
            diff = get_diffs_rgba(slicer)
            iio.imwrite(path, diff)
        elif path.exists():
            path.unlink()


if __name__ == "__main__":
    test_examples_run("simple")
    test_example_screenshots("simple")
