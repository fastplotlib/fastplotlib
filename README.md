# fastplotlib
[![CI](https://github.com/kushalkolar/fastplotlib/actions/workflows/ci.yml/badge.svg)](https://github.com/kushalkolar/fastplotlib/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/fastplotlib.svg)](https://badge.fury.io/py/fastplotlib)
[![Documentation Status](https://readthedocs.org/projects/fastplotlib/badge/?version=latest)](https://fastplotlib.readthedocs.io/en/latest/?badge=latest)
[![Gitter](https://badges.gitter.im/fastplotlib/community.svg)](https://gitter.im/fastplotlib/community?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge)

[**Installation**](https://github.com/kushalkolar/fastplotlib#installation) | [**GPU Drivers**](https://github.com/kushalkolar/fastplotlib#install-vulkan-drivers) | [**Examples**](https://github.com/kushalkolar/fastplotlib#examples) | **Contributing**

A fast plotting library built using the [`pygfx`](https://github.com/pygfx/pygfx) render engine utilizing [Vulkan](https://en.wikipedia.org/wiki/Vulkan) via WGPU, so it is very fast! We also aim to be an expressive plotting library that enables rapid prototyping for large scale explorative scientific visualization.

`fastplotlib` will work where that `pygfx` works, so that includes:
- `Jupyter lab`, using [`jupyter_rfb`](https://github.com/vispy/jupyter_rfb)
- `PyQt` and `PySide`
- `glfw`
- `wxPython`

Notes:
- It does not work in collab, for a detailed discussion see: https://github.com/vispy/jupyter_rfb/issues/57
- We do not officially support `jupyter notebook` through `jupyter_rfb`, there are weird issues. We recommend using `jupyter lab` until `jupyter notebook` switches to the `jupyter lab` backend in v7.
- You can use a non-blocking `glfw` canvas from a notebook, as long as you're working locally or have a way to forward the remote graphical desktop (such as X11 forwarding).

`fastplotlib` is currently in the **early alpha stage with breaking changes every ~week**, but you're welcome to try it out or contribute! See our [Roadmap for 2023](https://github.com/kushalkolar/fastplotlib/issues/55).

**Documentation**: http://fastplotlib.readthedocs.io/ 

The docs are not entirely thorough, we recommend the example notebooks to get started.

Questions, ideas? Post an issue or [chat on gitter](https://gitter.im/fastplotlib/community?utm_source=share-link&utm_medium=link&utm_campaign=share-link).

![epic](https://user-images.githubusercontent.com/9403332/210304473-f36f2aaf-319e-435b-bcc8-0e8d3e1ef282.gif)

# Installation

Install using `pip`.

### Minimal, use with your own `Qt` or `glfw` applications
```bash
pip install fastplotlib
```

### Notebook
```bash
pip install "fastplotlib[notebook]"
```

**Optional: install `simplejpeg` for much faster notebook visualization, you will need C compilers and [libjpeg-turbo](https://libjpeg-turbo.org/) to install it:**

```bash
pip install simplejpeg
```

**Note:** `fastplotlib` and `pygfx` are fast evolving projects, the version available through pip might be outdated, you will need to follow the "For Development" instructions below if you want the latest features. You can find the release history on pypi here: https://pypi.org/project/fastplotlib/#history 


# Examples

**Note: the examples on the `master` branch may require 

Clone or download the repo to try the examples

```bash
# clone the repo
git clone https://github.com/kushalkolar/fastplotlib.git

# IMPORTANT: if you are using a specific version from pip, checkout that version to get the examples which work for that version
# example:
# git checkout git checkout v0.1.0.a9 # replace "v0.1.0.a9" with the version you have

# cd into notebooks and launch jupyter lab
cd fastplotlib/notebooks
jupyter lab
```

**Start out with `simple.ipynb`.**

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

### Fast animations
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

## Graphics drivers

You will need a relatively modern GPU (newer integrated GPUs in CPUs are usually fine). Generally if your GPU is from 2017 or later it should be fine.

For more information see: https://wgpu-py.readthedocs.io/en/stable/start.html#platform-requirements

### Windows:
Vulkan drivers should be installed by default on Windows 11, but you will need to install your GPU manufacturer's driver package (Nvidia or AMD). If you have an integrated GPU within your CPU, you might still need to install a driver package too, check your CPU manufacturer's info.

We also recommend installing C compilers so that you can install `simplejpeg` which improves remote frame buffer performance in notebooks.

### Linux:
Debian based distros:

```bash
sudo apt install mesa-vulkan-drivers
# for better performance with the remote frame buffer install libjpeg-turbo
sudo apt install libjpeg-turbo
```

For other distros install the appropriate vulkan driver package, and optionally the corresponding `libjpeg-turbo` package for better remote-frame-buffer performance in jupyter notebooks.

#### CPU/software rendering (Lavapipe)

If you do not have a GPU you can perform limited software rendering using lavapipe. This should get you everything you need for that on Debian or Ubuntu based distros:

```bash
sudo apt install llvm-dev libturbojpeg* libgl1-mesa-dev libgl1-mesa-glx libglapi-mesa libglx-mesa0 mesa-common-dev mesa-vulkan-drivers
```

### Mac OSX:
As far as I know, WGPU uses Metal instead of Vulkan on Mac. You will need at least Mac OSX 10.13.

# Contributing

### Installation for developers
```bash
git clone https://github.com/kushalkolar/fastplotlib.git
cd fastplotlib

# install all extras in place
pip install -e ".[notebook,docs,tests]
```
