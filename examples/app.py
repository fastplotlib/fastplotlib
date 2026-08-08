from pathlib import Path
from collections import OrderedDict

import wgpu
from imgui_bundle import imgui
from wgpu.gui.auto import WgpuCanvas, run
from wgpu.utils.imgui import ImguiRenderer
import subprocess


canvas = WgpuCanvas(title="imgui", size=(1200, 900))
adapter = wgpu.gpu.request_adapter_sync(power_preference="high-performance")
device = adapter.request_device_sync()

imgui_renderer = ImguiRenderer(device, canvas)

example_paths: OrderedDict[Path, list[Path]] = OrderedDict()

# grab all examples as a dict of lists, {example_dir: [e1.py, e2.py, ...]}
for d in sorted(Path(__file__).parent.glob("*")):
    if d.is_dir():
        if d.name.startswith("."):
            continue
        if d.name in ["tests", "screenshots"]:
            continue
        example_paths[d] = sorted(d.glob("*.py"))

# the first example
example_dir0 = list(example_paths.keys())[0]
example0 = example_paths[example_dir0][0]

# set the first example to be selected
selection = (example_dir0, example0)

# read the first example
with open(selection[1], "r") as f:
    example_src = f.read()

# used to determine if a different example has been selected between frame draws
new_selection: bool = False


def update_gui():
    global selection
    global new_selection
    global example_src

    example_double_clicked = False

    w, h = canvas.get_physical_size()
    imgui.new_frame()

    menu_size = (340, h)
    menu_pos = (0, 0)

    imgui.set_next_window_size(menu_size)
    imgui.set_next_window_pos(menu_pos)

    flags = imgui.WindowFlags_.no_collapse | imgui.WindowFlags_.no_resize

    # window with the list of all examples
    imgui.begin("Examples", None, flags=flags)

    # add menu item for each example
    for example_dir in example_paths.keys():
        # each example dir
        imgui.text(example_dir.name)
        imgui.indent(10)

        # each individual example
        for example in example_paths[example_dir]:
            is_selected = selection[0] == example_dir and selection[1] == example
            selection_changed, selected = imgui.selectable(example.name, p_selected=is_selected)

            # update selection dir and path if this example file is selected
            if selected:
                selection = (example_dir, example)
                # if double-clicked, used to flag running the example
                if imgui.is_mouse_double_clicked(0):
                    example_double_clicked = True

            if selection_changed:
                # new example file is selected on this frame update
                new_selection = True

        imgui.unindent(10)
        imgui.separator()

    imgui.end()

    # window that displays text of example
    source_window_size = (w - menu_size[0], h)
    imgui.set_next_window_size(source_window_size)
    imgui.set_next_window_pos((menu_size[0], 0))

    imgui.begin(f"{selection[0].name}/{selection[1].name}", None, flags)

    # path to the selected example file
    selected_example = selection[1]

    # if this example file has just been selected in this render frame update
    # then update the example_src by reading the file from disk
    if new_selection:
        with open(selected_example, "r") as f:
             example_src = f.read()

        # new_selection = False prevents it from reading from disk every time the frame is rendered
        # this allows any changes from the user to be kept, while the file on disk remains unchanged
        # so the user can make a small change to the file in the text editor and run it with the changes!
        new_selection = False

    # basic text editor
    src_changed, example_src = imgui.input_text_multiline(".", example_src, (source_window_size[0], h - 60))

    clicked = imgui.button("Run example")

    # run the example if the button is clicked or if the item is double-clicked
    if clicked or example_double_clicked:
        subprocess.Popen(["python", "-c", example_src])

    imgui.end()

    imgui.end_frame()
    imgui.render()

    return imgui.get_draw_data()


# set the GUI update function that gets called to return the draw data
imgui_renderer.set_gui(update_gui)


def draw_frame():
    imgui_renderer.render()
    canvas.request_draw()


if __name__ == "__main__":
    canvas.request_draw(draw_frame)
    run()
