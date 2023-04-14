import pygfx
from typing import *

camera_types = {
    '2d': pygfx.OrthographicCamera,
    '3d': pygfx.PerspectiveCamera,
}

controller_types = {
    '2d': pygfx.PanZoomController,
    '3d': pygfx.OrbitController,
    pygfx.OrthographicCamera: pygfx.PanZoomController,
    pygfx.PerspectiveCamera: pygfx.OrbitController,
}


def create_camera(camera_type: str, big_camera: bool = False) -> Union[pygfx.OrthographicCamera, pygfx.PerspectiveCamera]:
    camera_type = camera_type.split("-")

    # kinda messy but works for now
    if len(camera_type) > 1:
        if camera_type[1] == "big":
            big_camera = True

        camera_type = camera_type[0]
    else:
        camera_type = camera_type[0]

    cls = camera_types[camera_type]

    if cls is pygfx.OrthographicCamera:
        if big_camera:
            return cls(1024, 1024, -8192, 8192)
        else:
            return cls(1024, 1024)

    else:
        return cls()


def create_controller(controller_type: str):
    controller_type = controller_type.split("-")[0]

    return controller_types[controller_type]()
