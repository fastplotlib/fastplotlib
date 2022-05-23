import pygfx

camera_types = {
    '2d': pygfx.OrthographicCamera,
    '3d': pygfx.PerspectiveCamera,
}
controller_types = {
    '2d': pygfx.PanZoomController,
    '3d': pygfx.OrbitOrthoController,
    pygfx.OrthographicCamera: pygfx.PanZoomController,
    pygfx.PerspectiveCamera: pygfx.OrbitOrthoController,
}
