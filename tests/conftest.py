import pygfx

import pytest


MAX_TEXTURE_SIZE = 1024


@pytest.fixture(scope="session", autouse=True)
def set_wgpu_texture_limit():
    pygfx.renderers.wgpu.set_wgpu_limits(**{"max-texture-dimension2d": MAX_TEXTURE_SIZE})
    yield
