"""
Test that examples run without error.
"""
import importlib
import runpy
import pytest
import os
import numpy as np

from .testutils import (
    ROOT,
    examples_dir,
    screenshots_dir,
    find_examples,
    wgpu_backend,
    is_lavapipe,
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
def test_example_screenshots(module, force_offscreen, regenerate_screenshots=False):
    """Make sure that every example marked outputs the expected."""
    # (relative) module name from project root
    module_name = module.relative_to(ROOT/"examples").with_suffix("").as_posix().replace("/", ".")

    # import the example module
    example = importlib.import_module(module_name)

    # render a frame
    img = np.asarray(example.renderer.target.draw())

    # check if _something_ was rendered
    assert img is not None and img.size > 0

    # if screenshots dir does not exist, will create and generate screenshots
    if not os.path.exists(screenshots_dir):
        os.mkdir(screenshots_dir)

    screenshot_path = screenshots_dir / f"{module.stem}.npy"

    if regenerate_screenshots:
        np.save(screenshot_path, img)

    assert (
        screenshot_path.exists()
    ), "found # test_example = true but no reference screenshot available"
    stored_img = np.load(screenshot_path)
    is_similar = np.allclose(img, stored_img, atol=1)
    assert is_similar


if __name__ == "__main__":
    test_examples_run("simple")
    test_example_screenshots("simple", regenerate_screenshots=True)
