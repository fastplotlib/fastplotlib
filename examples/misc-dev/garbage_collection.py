import numpy as np
from wgpu.gui.auto import WgpuCanvas, run
import pygfx as gfx
import subprocess

canvas = WgpuCanvas()
renderer = gfx.WgpuRenderer(canvas)
scene = gfx.Scene()
camera = gfx.OrthographicCamera(5000, 5000)
camera.position.x = 2048
camera.position.y = 2048


def make_image():
    data = np.random.rand(4096, 4096).astype(np.float32)

    return gfx.Image(
        gfx.Geometry(grid=gfx.Texture(data, dim=2)),
        gfx.ImageBasicMaterial(clim=(0, 1)),
    )


def draw():
    renderer.render(scene, camera)
    canvas.request_draw()


def print_nvidia(msg=""):
    print(msg)
    print(
        subprocess.check_output(
            ["nvidia-smi", "--format=csv", "--query-gpu=memory.used"]
        )
        .decode()
        .split("\n")[1]
    )
    print()


def add_img(*args):
    print_nvidia("Before creating image")
    img = make_image()
    print_nvidia("After creating image")
    scene.add(img)
    img.add_event_handler(remove_img, "click")
    draw()
    print_nvidia("After add image to scene")


def remove_img(*args):
    img = scene.children[0]
    scene.remove(img)
    draw()
    print_nvidia("After remove image from scene")
    del img
    draw()
    print_nvidia("After del image")
    renderer.add_event_handler(print_nvidia, "pointer_move")


renderer.add_event_handler(add_img, "double_click")

draw()
run()
