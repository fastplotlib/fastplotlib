import pygfx
from typing import *

camera_types = {
    "2d": pygfx.OrthographicCamera,
    "3d": pygfx.PerspectiveCamera,
}


def create_camera(
    camera_type: Union[pygfx.Camera, str],
    big_camera: bool = False
) -> Union[pygfx.OrthographicCamera, pygfx.PerspectiveCamera]:
    if isinstance(camera_type, (pygfx.OrthographicCamera, pygfx.PerspectiveCamera)):
        return camera_type

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


def create_controller(
    camera: Union[pygfx.OrthographicCamera, pygfx.PerspectiveCamera],
    controller: Union[pygfx.Controller, None, str],
) -> pygfx.Controller:
    if isinstance(controller, pygfx.Controller):
        return controller

    if controller is None:
        # default controllers
        if camera == "2d" or isinstance(camera, pygfx.OrthographicCamera):
            return pygfx.PanZoomController(camera)

        elif camera == "3d" or isinstance(camera, pygfx.PerspectiveCamera):
            return pygfx.FlyController(camera)

    # controller specified
    if controller == "fly":
        return pygfx.FlyController(camera)

    elif controller == "panzoom":
        return pygfx.PanZoomController(camera)

    elif controller == "trackball":
        return pygfx.TrackballController(camera)

    elif controller == "orbit":
        return pygfx.OrbitController(camera)

    else:
        raise ValueError(
            f"Invalid controller type, valid controllers are instances of `pygfx.Controller` or one of:\n"
            f"'panzoom', 'fly', 'trackball', or 'orbit'. You have passed: {type(controller)}"
        )
