import os

import numpy as np
import pytest

import fastplotlib as fpl
import pygfx


@pytest.fixture(scope="session", autouse=True)
def set_env():
    os.environ["WGPU_FORCE_OFFSCREEN"] = "true"


def test_cameras_controller_properties():
    cameras = [
        ["2d", "3d", "3d"],
        ["3d", "3d", "3d"]
    ]

    controller_types = [
        ["panzoom", "panzoom", "fly"],
        ["orbit", "trackball", "panzoom"]
    ]

    gp = fpl.GridPlot(
        shape=(2, 3),
        cameras=cameras,
        controller_types=controller_types
    )

    subplot_cameras = [subplot.camera for subplot in gp]
    subplot_controllers = [subplot.controller for subplot in gp]

    for c1, c2 in zip(subplot_cameras, gp.cameras.ravel()):
        assert c1 is c2

    for c1, c2 in zip(subplot_controllers, gp.controllers.ravel()):
        assert c1 is c2

    for camera_type, subplot_camera in zip(np.asarray(cameras).ravel(), gp.cameras.ravel()):
        if camera_type == "2d":
            assert subplot_camera.fov == 0
        else:
            assert subplot_camera.fov == 50

    for controller_type, subplot_controller in zip(np.asarray(controller_types).ravel(), gp.controllers.ravel()):
        match controller_type:
            case "panzoom":
                assert isinstance(subplot_controller, pygfx.PanZoomController)
            case "fly":
                assert isinstance(subplot_controller, pygfx.FlyController)
            case "orbit":
                assert isinstance(subplot_controller, pygfx.OrbitController)
            case "trackball":
                assert isinstance(subplot_controller, pygfx.TrackballController)

    # check changing cameras
    gp[0, 0].camera = "3d"
    assert gp[0, 0].camera.fov == 50
    gp[1, 0].camera = "2d"
    assert gp[1, 0].camera.fov == 0

    # test changing controller
    gp[1, 1].controller = "fly"
    assert isinstance(gp[1, 1].controller, pygfx.FlyController)
    assert gp[1, 1].controller is gp.controllers[1, 1]
    gp[0, 2].controller = "panzoom"
    assert isinstance(gp[0, 2].controller, pygfx.PanZoomController)
    assert gp[0, 2].controller is gp.controllers[0, 2]


def test_gridplot_controller_ids_int():
    ids = [
        [0, 1, 1],
        [0, 2, 3],
        [4, 1, 2]
    ]

    gp = fpl.GridPlot(shape=(3, 3), controller_ids=ids)

    assert gp[0, 0].controller is gp[1, 0].controller
    assert gp[0, 1].controller is gp[0, 2].controller is gp[2, 1].controller
    assert gp[1, 1].controller is gp[2, 2].controller


def test_gridplot_controller_ids_int_change_controllers():
    ids = [
        [0, 1, 1],
        [0, 2, 3],
        [4, 1, 2]
    ]

    cameras = [
        ["2d", "3d", "3d"],
        ["2d", "3d", "2d"],
        ["3d", "3d", "3d"]
    ]

    gp = fpl.GridPlot(shape=(3, 3), cameras=cameras, controller_ids=ids)

    assert isinstance(gp[0, 1].controller, pygfx.FlyController)

    # changing controller when id matches should change the others too
    gp[0, 1].controller = "panzoom"
    assert isinstance(gp[0, 1].controller, pygfx.PanZoomController)
    assert gp[0, 1].controller is gp[0, 2].controller is gp[2, 1].controller
    assert set(gp[0, 1].controller.cameras) == {gp[0, 1].camera, gp[0, 2].camera, gp[2, 1].camera}

    # change to orbit
    gp[0, 1].controller = "orbit"
    assert isinstance(gp[0, 1].controller, pygfx.OrbitController)
    assert gp[0, 1].controller is gp[0, 2].controller is gp[2, 1].controller
    assert set(gp[0, 1].controller.cameras) == {gp[0, 1].camera, gp[0, 2].camera, gp[2, 1].camera}


def test_gridplot_controller_ids_str():
    names = [
        ["a", "b", "c"],
        ["d", "e", "f"]
    ]

    controller_ids = [
        ["a", "f"],
        ["b", "d", "e"]
    ]

    gp = fpl.GridPlot(shape=(2, 3), controller_ids=controller_ids, names=names)

    assert gp[0, 0].controller is gp[1, 2].controller is gp["a"].controller is gp["f"].controller
    assert gp[0, 1].controller is gp[1, 0].controller is gp[1, 1].controller is gp["b"].controller is gp["d"].controller is gp["e"].controller

    # make sure subplot c is unique
    exclude_c = [gp[n].controller for n in ["a", "b", "d", "e", "f"]]
    assert gp["c"] not in exclude_c


def test_set_gridplot_controllers_from_existing_controllers():
    gp = fpl.GridPlot(shape=(3, 3))
    gp2 = fpl.GridPlot(shape=gp.shape, controllers=gp.controllers)

    assert gp.controllers[:-1].size == 6
    with pytest.raises(ValueError):
        gp3 = fpl.GridPlot(shape=gp.shape, controllers=gp.controllers[:-1])

    for sp_gp, sp_gp2 in zip(gp, gp2):
        assert sp_gp.controller is sp_gp2.controller

    cameras = [
        [pygfx.PerspectiveCamera(), "3d"],
        ["3d", "2d"]
    ]

    controllers = [
        [pygfx.FlyController(cameras[0][0]), pygfx.TrackballController()],
        [pygfx.OrbitController(), pygfx.PanZoomController()]
    ]

    gp = fpl.GridPlot(shape=(2, 2), cameras=cameras, controllers=controllers)

    assert gp[0, 0].controller is controllers[0][0]
    assert gp[0, 1].controller is controllers[0][1]
    assert gp[1, 0].controller is controllers[1][0]
    assert gp[1, 1].controller is controllers[1][1]

    assert gp[0, 0].camera is cameras[0][0]

    assert gp[0, 1].camera.fov == 50
