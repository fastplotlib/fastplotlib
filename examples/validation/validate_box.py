"""
Box Geometry
============

Example showing the box geometry.
"""
# test_example = true
# sphinx_gallery_pygfx_render = True

from wgpu.gui.auto import WgpuCanvas, run
import pygfx as gfx

canvas = WgpuCanvas()
renderer = gfx.renderers.WgpuRenderer(canvas)

scene = gfx.Scene()

material = gfx.MeshBasicMaterial(color=(1, 0, 0), wireframe=True, wireframe_thickness=3)
geometry = gfx.box_geometry(1, 2, 3)
box = gfx.Mesh(geometry, material)
scene.add(box)

material2 = gfx.MeshNormalLinesMaterial(color=(0, 1, 0), line_length=0.5)
box2 = gfx.Mesh(geometry, material2)
scene.add(box2)

camera = gfx.OrthographicCamera(5, 5)
camera.position.set(5, 5, 5)
camera.look_at(gfx.linalg.Vector3())

canvas.request_draw(lambda: renderer.render(scene, camera))

if __name__ == "__main__":
    print(__doc__)
    run()
