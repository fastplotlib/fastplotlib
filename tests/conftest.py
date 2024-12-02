import pygfx


MAX_TEXTURE_SIZE = 1024


def pytest_sessionstart(session):
    pygfx.renderers.wgpu.set_wgpu_limits(**{"max-texture-dimension-2d": MAX_TEXTURE_SIZE})
