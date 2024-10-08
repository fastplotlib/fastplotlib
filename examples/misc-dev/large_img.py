from fastplotlib import Plot, run
import numpy as np

temporal = np.load("./array_10-000x108-000.npy")

from PIL import Image

Image.MAX_IMAGE_PIXELS = None

img = Image.open("/home/kushal/Downloads/gigahour_stitched_0042_bbs.png")

a = np.array(img)

r = np.random.randint(0, 50, a.size, dtype=np.uint8).reshape(a.shape)

plot = Plot(renderer_kwargs={"show_fps": True})
plot.add_heatmap(r)
# plot.camera.scale.y = 0.2
plot.show()

r = np.random.randint(0, 50, a.size, dtype=np.uint8).reshape(a.shape)
r2 = np.random.randint(0, 50, a.size, dtype=np.uint8).reshape(a.shape)
r3 = np.random.randint(0, 50, a.size, dtype=np.uint8).reshape(a.shape)

rs = [r, r2, r3]
i = 0

def update_frame(p):
    global i
    p.graphics[0].data[:] = rs[i % 3]
    i +=1
    
plot.add_animations(update_frame)

run()
