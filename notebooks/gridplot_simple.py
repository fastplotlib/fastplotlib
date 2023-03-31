import numpy as np
from wgpu.gui.auto import WgpuCanvas
import pygfx as gfx
from fastplotlib.layouts import GridPlot
from fastplotlib.graphics import ImageGraphic, LineGraphic, HistogramGraphic
from fastplotlib import run
from math import sin, cos, radians

# GridPlot of shape 2 x 3
grid_plot = GridPlot(shape=(2, 3))

image_graphics = list()

hist_data1 = np.random.normal(0, 256, 2048)
hist_data2 = np.random.poisson(0, 256)

# Make a random image graphic for each subplot
for i, subplot in enumerate(grid_plot):
    img = np.random.rand(512, 512) * 255
    ig = ImageGraphic(data=img, vmin=0, vmax=255, cmap='gnuplot2')
    image_graphics.append(ig)

    # add the graphic to the subplot
    subplot.add_graphic(ig)

    histogram = HistogramGraphic(data=hist_data1, bins=100)
    histogram.world_object.rotation.w = cos(radians(45))
    histogram.world_object.rotation.z = sin(radians(45))

    histogram.world_object.scale.y = 1
    histogram.world_object.scale.x = 8

    for dv_position in ["right", "top", "bottom", "left"]:
        h2 = HistogramGraphic(data=hist_data1, bins=100)

        subplot.docked_viewports[dv_position].size = 60
        subplot.docked_viewports[dv_position].add_graphic(h2)
#

# Define a function to update the image graphics
# with new randomly generated data
def set_random_frame():
    for ig in image_graphics:
        new_data = np.random.rand(512, 512) * 255
        ig.update_data(data=new_data)


# add the animation
# grid_plot.add_animations(set_random_frame)

grid_plot.show()

run()
