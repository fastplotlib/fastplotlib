"""
Vizualizing Multi-Object Tracking
=================================

By sharing the scene between subplots, we can dynamically add detail views for each detected object.
"""
# %% imports
import fastplotlib as fpl
import numpy as np
import imageio.v3 as iio



# %% Mock data
# TODO: replace with YOLO-tracking/detection example?


movie = iio.imread("imageio:cockatoo.mp4")
# make shape (t, h, w, 1) (for monochrome examples)
movie = movie[:,:,:, 0] # take one channel
print(movie.shape)

# boxes are are x,y,w,h... but there can be multiple per frame - so it's a list of boxes that can also be empty.
center_path = np.array([[movie.shape[2]/2 + 200*np.sin(t/30), movie.shape[1]/2 + 50*np.cos(t/5)] for t in range(len(movie)-60)])
width = 80 + 20*np.sin(np.linspace(0, 10*np.pi, len(movie)-60))
height = 100 + 30*np.cos(np.linspace(0, 8*np.pi, len(movie)-60))
bboxes = {t+30: [[center_path[t][0]-width[t]/2, center_path[t][1]-height[t]/2, width[t], height[t]]] for t in range(len(movie)-60)}
# add a bit of jitter noise and some dropouts
fake_preds = {}
for t in bboxes:
    fake_preds[t] = [box.copy() for box in bboxes[t]]
    for box in fake_preds[t]:
        box[0] += np.random.normal(scale=5.0)
        box[1] += np.random.normal(scale=5.0)
        box[2] += np.random.normal(scale=3.0)
        box[3] += np.random.normal(scale=8.0)
    # fake_preds[t] = [box.copy() for box in bboxes[t]]
    if np.random.rand() < 0.1:
        fake_preds[t] = []

def get_lines(box) -> fpl.LineGraphic:
    # convert boxes to line graphics so they can be added to a LineGraphicCollection during runtime.
    lines = []
    x, y, w, h = box
    lines.append([x-0.5*w, y+0.5*h]) # top left
    lines.append([x+0.5*w, y+0.5*h]) # top right
    lines.append([x+0.5*w, y-0.5*h]) # bottom right
    lines.append([x-0.5*w, y-0.5*h]) # bottom left
    lines.append(lines[0]) # close box
    return fpl.LineGraphic(np.array(lines), alpha=0.95)


# %% make the plot
global iw
# TODO: can this constructor be done with just one data? (multiple views?)
iw = fpl.ImageWidget(data=[movie,movie], rgb=False, cmap="white", figure_shape=(1,2), figure_kwargs={"size" : (1400, 650), "controller_ids": [[0,1]], "scene_ids": "sync"}, graphic_kwargs={"vmin": 0, "vmax": 255})
# TODO: remove the 2nd Histogram tool (it's shared now.)

iw._image_widget_sliders._fps["t"] = 30 # not exposed
figure: fpl.Figure = iw.figure
# can these be zero init too?
box_overlay = figure[0,0].add_line_collection(data=[])

# TODO: in the right subplot, add one detail box per detected object--- automatically open and close them?

figure[0,1].axes.visible = False
figure[0,1].toolbar = False

def update_overlay(index):
    t = index["t"]

    # clean up old boxes:
    for g in box_overlay.graphics:
        box_overlay.remove_graphic(g)
        # pass

    label_boxes = bboxes.get(t, [])
    for label in label_boxes:
        lines = get_lines(label)
        lines.colors = "red" # red for labels
        box_overlay.add_graphic(lines)
    
    pred_boxes = fake_preds.get(t, [])
    for pred in pred_boxes:
        lines = get_lines(pred)
        lines.colors = "green" # green for predictions
        # maybe get confidence for alpha or something fun
        box_overlay.add_graphic(lines)

    # update crop:
    if label_boxes:
        long_edge = max(label_boxes[0][2], label_boxes[0][3]) # here we lose multiple objects
        # TODO: make this behave better (based on a relative value?)
        scale = 100 / long_edge 
        figure[0,1].camera.set_state({"position": (label_boxes[0][0], label_boxes[0][1], -1), "zoom": scale})


iw.add_event_handler(update_overlay)
iw.show()


# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
