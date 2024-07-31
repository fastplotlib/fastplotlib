import numpy as np
import pytest

import fastplotlib as fpl
import pygfx


def test_cameras_controller_properties():
    cameras = [["2d", "3d", "3d"], ["3d", "3d", "3d"]]

    controller_types = [
        ["panzoom", "panzoom", "fly"],
        ["orbit", "trackball", "panzoom"],
    ]

    fig = fpl.Figure(
        shape=(2, 3),
        cameras=cameras,
        controller_types=controller_types,
        canvas="offscreen",
    )

    print(fig.canvas)

    subplot_cameras = [subplot.camera for subplot in fig]
    subplot_controllers = [subplot.controller for subplot in fig]

    for c1, c2 in zip(subplot_cameras, fig.cameras.ravel()):
        assert c1 is c2

    for c1, c2 in zip(subplot_controllers, fig.controllers.ravel()):
        assert c1 is c2

    for camera_type, subplot_camera in zip(
        np.asarray(cameras).ravel(), fig.cameras.ravel()
    ):
        if camera_type == "2d":
            assert subplot_camera.fov == 0
        else:
            assert subplot_camera.fov == 50

    for controller_type, subplot_controller in zip(
        np.asarray(controller_types).ravel(), fig.controllers.ravel()
    ):
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
    fig[0, 0].camera = "3d"
    assert fig[0, 0].camera.fov == 50
    fig[1, 0].camera = "2d"
    assert fig[1, 0].camera.fov == 0

    # test changing controller
    fig[1, 1].controller = "fly"
    assert isinstance(fig[1, 1].controller, pygfx.FlyController)
    assert fig[1, 1].controller is fig.controllers[1, 1]
    fig[0, 2].controller = "panzoom"
    assert isinstance(fig[0, 2].controller, pygfx.PanZoomController)
    assert fig[0, 2].controller is fig.controllers[0, 2]


def test_controller_ids_int():
    ids = [[0, 1, 1], [0, 2, 3], [4, 1, 2]]

    fig = fpl.Figure(shape=(3, 3), controller_ids=ids, canvas="offscreen")

    assert fig[0, 0].controller is fig[1, 0].controller
    assert fig[0, 1].controller is fig[0, 2].controller is fig[2, 1].controller
    assert fig[1, 1].controller is fig[2, 2].controller


def test_controller_ids_int_change_controllers():
    ids = [[0, 1, 1], [0, 2, 3], [4, 1, 2]]

    cameras = [["2d", "3d", "3d"], ["2d", "3d", "2d"], ["3d", "3d", "3d"]]

    fig = fpl.Figure(
        shape=(3, 3), cameras=cameras, controller_ids=ids, canvas="offscreen"
    )

    assert isinstance(fig[0, 1].controller, pygfx.FlyController)

    # changing controller when id matches should change the others too
    fig[0, 1].controller = "panzoom"
    assert isinstance(fig[0, 1].controller, pygfx.PanZoomController)
    assert fig[0, 1].controller is fig[0, 2].controller is fig[2, 1].controller
    assert set(fig[0, 1].controller.cameras) == {
        fig[0, 1].camera,
        fig[0, 2].camera,
        fig[2, 1].camera,
    }

    # change to orbit
    fig[0, 1].controller = "orbit"
    assert isinstance(fig[0, 1].controller, pygfx.OrbitController)
    assert fig[0, 1].controller is fig[0, 2].controller is fig[2, 1].controller
    assert set(fig[0, 1].controller.cameras) == {
        fig[0, 1].camera,
        fig[0, 2].camera,
        fig[2, 1].camera,
    }


def test_controller_ids_str():
    names = [["a", "b", "c"], ["d", "e", "f"]]

    controller_ids = [["a", "f"], ["b", "d", "e"]]

    fig = fpl.Figure(
        shape=(2, 3), controller_ids=controller_ids, names=names, canvas="offscreen"
    )

    assert (
        fig[0, 0].controller
        is fig[1, 2].controller
        is fig["a"].controller
        is fig["f"].controller
    )
    assert (
        fig[0, 1].controller
        is fig[1, 0].controller
        is fig[1, 1].controller
        is fig["b"].controller
        is fig["d"].controller
        is fig["e"].controller
    )

    # make sure subplot c is unique
    exclude_c = [fig[n].controller for n in ["a", "b", "d", "e", "f"]]
    assert fig["c"] not in exclude_c


def test_set_controllers_from_existing_controllers():
    fig = fpl.Figure(shape=(3, 3), canvas="offscreen")
    fig2 = fpl.Figure(shape=fig.shape, controllers=fig.controllers, canvas="offscreen")

    assert fig.controllers[:-1].size == 6
    with pytest.raises(ValueError):
        fig3 = fpl.Figure(
            shape=fig.shape, controllers=fig.controllers[:-1], canvas="offscreen"
        )

    for fig1_subplot, fig2_subplot in zip(fig, fig2):
        assert fig1_subplot.controller is fig2_subplot.controller

    cameras = [[pygfx.PerspectiveCamera(), "3d"], ["3d", "2d"]]

    controllers = [
        [pygfx.FlyController(cameras[0][0]), pygfx.TrackballController()],
        [pygfx.OrbitController(), pygfx.PanZoomController()],
    ]

    fig = fpl.Figure(
        shape=(2, 2), cameras=cameras, controllers=controllers, canvas="offscreen"
    )

    assert fig[0, 0].controller is controllers[0][0]
    assert fig[0, 1].controller is controllers[0][1]
    assert fig[1, 0].controller is controllers[1][0]
    assert fig[1, 1].controller is controllers[1][1]

    assert fig[0, 0].camera is cameras[0][0]

    assert fig[0, 1].camera.fov == 50
