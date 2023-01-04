# fastplotlib
[![Gitter](https://badges.gitter.im/fastplotlib/community.svg)](https://gitter.im/fastplotlib/community?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge)

A fast plotting library built using the [`pygfx`](https://github.com/pygfx/pygfx) render engine utilizing [Vulkan](https://en.wikipedia.org/wiki/Vulkan) via WGPU, so it is very fast! `fastplotlib` is focussed on very fast interactive plotting in the notebook using an expressive API. It also works within desktop applications using `glfw` or `Qt`.

`fastplotlib` is currently in the early alpha stage with breaking changes every ~week, but you're welcome to try it out or contribute! See our [Roadmap for 2023](https://github.com/kushalkolar/fastplotlib/issues/55).

Questions, ideas? Post an issue or [chat on gitter](https://gitter.im/fastplotlib/community?utm_source=share-link&utm_medium=link&utm_campaign=share-link).

![epic](https://user-images.githubusercontent.com/9403332/210304473-f36f2aaf-319e-435b-bcc8-0e8d3e1ef282.gif)

# Examples

**See the examples directory. Start out with `simple.ipynb`.**

### Neuroscience usecase demonstrating some of fastplotlib's capabilities

https://user-images.githubusercontent.com/9403332/210304485-e554b648-50b4-4243-b292-a9ed30514a2d.mp4

### Simple image plot
```python
from fastplotlib import Plot
import numpy as np

plot = Plot()

data = np.random.rand(512, 512)
plot.add_image(data=data)

plot.show()
```
![image](https://user-images.githubusercontent.com/9403332/209422734-4f983b42-e126-40a7-a681-3b8e22dbd797.png)

### Fast image updates
```python
from fastplotlib import Plot
import numpy as np

plot = Plot()

data = np.random.rand(512, 512)
image = plot.image(data=data)

def update_data():
    new_data = np.random.rand(512, 512)
    image.data = new_data

plot.add_animations(update_data)

plot.show()
```

![out](https://user-images.githubusercontent.com/9403332/209422871-6b2153f3-81ca-4f62-9200-8206a81eaf0d.gif)

### Interactivity

![interact](https://user-images.githubusercontent.com/9403332/210027199-6e4ac193-6096-4d18-80d5-a41591ea4d4f.gif)

This is all in the notebook and non-blocking!

### Image widget

Interactive visualization of large imaging datasets in the notebook.

![zfish](https://user-images.githubusercontent.com/9403332/209711810-abdb7d1d-81ce-4874-80f5-082efa2c421d.gif)


# Installation

Install directly from GitHub using `pip`.

```bash
pip install git+https://github.com/kushalkolar/fastplotlib.git
```

Note: do not download the version that is currently on PYPI (i.e. don't just do `pip install fastplotlib`, it is outdated (we're waiting for the next release of `pygfx`)

**Installing `simplejpeg` is recommended for faster plotting in notebooks using rfb. You will need C compilers setup on your computer to install it:**

```bash
pip install simplejpeg
```

Clone or download the repo to try the examples

```bash
# clone the repo
git clone https://github.com/kushalkolar/fastplotlib.git

# cd into examples and launch jupyter lab
cd fastplotlib/examples
jupyter lab
```

You will need a GPU that supports Vulkan (iGPUs in CPUs should be fine). Generally if your GPU is from 2017 or later it should support Vulkan. See the section on "Install Vulkan drivers" below for more information.

### For Development

```bash
git clone https://github.com/kushalkolar/fastplotlib.git
cd fastplotlib
pip install -r requirements.txt
pip install -e .

# try the examples
cd examples
jupyter lab
```

## Install Vulkan drivers

For more information see: https://github.com/pygfx/wgpu-py#platform-requirements

### Windows:
Vulkan should be installed by default on Windows 11, but you will need to install your GPU manufacturer's driver package (Nvidia or AMD). If you have an integrated GPU within your CPU, you might still need to install a driver package too, check your CPU manufacturer's info.

### Linux:
Debian based distros:

```bash
sudo apt install mesa-vulkan-drivers
# for better performance with the remote frame buffer install libjpeg-turbo
sudo apt install libjpeg-turbo
```

For other distros install the appropriate vulkan driver package, and optionally the corresponding `libjpeg-turbo` package for better remote-frame-buffer performance in jupyter notebooks.

### Mac OSX:
You will need at least MacOSX v10.13, not sure how to install Vulkan drivers on Mac. If anyone knows you can add instructions here!

# Gallery

### Extremely fast image updates, 5 x 5 gridplot

https://www.youtube.com/embed/-_0Gp_EqepI

### Very fast image updates with some synced controllers

https://user-images.githubusercontent.com/9403332/165678225-dcf3b401-86a5-4df5-a9e5-dc65bdb0443a.mp4

### 4x Grid of Scatter plots, 1.2 million points each

[https://user-images.githubusercontent.com/9403332/165677576-a0aa2d0f-a201-4e0e-91bd-aed800f775ee.mp4](https://www.youtube.com/watch?v=j_gwi-Wf1Ao)

### Lineplot

https://user-images.githubusercontent.com/9403332/165678270-aea65a83-6cc1-4edc-981c-4857eaf293c7.mp4

