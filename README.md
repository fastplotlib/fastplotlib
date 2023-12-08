<p align="center">
<img src="https://github.com/fastplotlib/fastplotlib/blob/main/docs/source/fastplotlib_logo.svg" height="220" alt="logo">
</p>

---

[![CI](https://github.com/kushalkolar/fastplotlib/actions/workflows/ci.yml/badge.svg)](https://github.com/kushalkolar/fastplotlib/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/fastplotlib.svg)](https://badge.fury.io/py/fastplotlib)
[![Documentation Status](https://readthedocs.org/projects/fastplotlib/badge/?version=latest)](https://fastplotlib.readthedocs.io/en/latest/?badge=latest)
[![Gitter](https://badges.gitter.im/fastplotlib/community.svg)](https://gitter.im/fastplotlib/community?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge)

[**Installation**](https://github.com/kushalkolar/fastplotlib#installation) | 
[**GPU Drivers**](https://github.com/kushalkolar/fastplotlib#graphics-drivers) | 
[**Documentation**](https://github.com/fastplotlib/fastplotlib#documentation) | 
[**Examples**](https://github.com/kushalkolar/fastplotlib#examples) | 
[**Contributing**](https://github.com/kushalkolar/fastplotlib#heart-contributing)

Next-gen plotting library built using the [`pygfx`](https://github.com/pygfx/pygfx) rendering engine that can utilize [Vulkan](https://en.wikipedia.org/wiki/Vulkan), [DX12](https://en.wikipedia.org/wiki/DirectX#DirectX_12), or [Metal](https://developer.apple.com/metal/) via WGPU, so it is very fast! We also aim to be an expressive plotting library that enables rapid prototyping for large scale explorative scientific visualization.

![scipy-fpl](https://github.com/fastplotlib/fastplotlib/assets/9403332/b981a54c-05f9-443f-a8e4-52cd01cd802a)

### SciPy 2023 Talk

[![fpl_thumbnail](http://i3.ytimg.com/vi/Q-UJpAqljsU/hqdefault.jpg)](https://www.youtube.com/watch?v=Q-UJpAqljsU)

Notebooks from talk: https://github.com/fastplotlib/fastplotlib-scipy2023 


# Supported frameworks

`fastplotlib` can run on anything that [`pygfx`](https://github.com/pygfx/pygfx) can also run, this includes:

:heavy_check_mark: `Jupyter lab`, using [`jupyter_rfb`](https://github.com/vispy/jupyter_rfb)\
:heavy_check_mark: `PyQt` and `PySide`\
:heavy_check_mark: `glfw`\
:heavy_check_mark: `wxPython`

**Notes:**\
:heavy_check_mark: Non-blocking Qt output is supported in ipython and notebooks by using [`%gui qt`](https://ipython.readthedocs.io/en/stable/interactive/magics.html#magic-gui) before creating plots. This hook only supports pyqt6 at the moment.\
:grey_exclamation: We do not officially support `jupyter notebook` through `jupyter_rfb`, this may change with notebook v7\
:disappointed: [`jupyter_rfb`](https://github.com/vispy/jupyter_rfb) does not work in collab yet, see https://github.com/vispy/jupyter_rfb/pull/77 

> **Note**
> 
> `fastplotlib` is currently in the **alpha stage with breaking changes every ~month**, but you're welcome to try it out or contribute! See our [Roadmap](https://github.com/kushalkolar/fastplotlib/issues/55). See this for a discussion on API stability: https://github.com/fastplotlib/fastplotlib/issues/121 

# Documentation

http://fastplotlib.readthedocs.io/ 

The Quickstart guide is not interactive. We recommend cloning/downloading the repo and trying out the `desktop` or `notebook` examples: https://github.com/kushalkolar/fastplotlib/tree/main/examples

If someone wants to integrate `pyodide` with `pygfx` we would be able to have live interactive examples! :smiley:

Questions, issues, ideas? Post an [issue](https://github.com/fastplotlib/fastplotlib/issues) or post on the [discussion forum](https://github.com/fastplotlib/fastplotlib/discussions)!

# Installation

Install using `pip`.

### Minimal, use with your own `Qt` or `glfw` applications
```bash
pip install fastplotlib
```

**This does not give you `Qt` or `glfw`, you will have to install one of them yourself depending on your preference**.

### Notebook
```bash
pip install "fastplotlib[notebook]"
```

**Optional: install `simplejpeg` for much faster notebook visualization**

```bash
pip install simplejpeg
```

> **Note**
>
> `fastplotlib` and `pygfx` are fast evolving projects, the version available through pip might be outdated, you will need to follow the "For developers" instructions below if you want the latest features. You can find the release history on pypi here: https://pypi.org/project/fastplotlib/#history

### For developers
```bash
git clone https://github.com/kushalkolar/fastplotlib.git
cd fastplotlib

# install all extras in place
pip install -e ".[notebook,docs,tests]"
```

# Examples

> **Note**
> 
> `fastplotlib` and `pygfx` are fast evolving, you may require the latest `pygfx` and `fastplotlib` from github to use the examples in the main branch.

Note that `fastplotlib` code is basically identical between desktop and notebook usage. The differences are:
- Running in `glfw` requires a `fastplotlib.run()` call (which is really just a `wgpu` `run()` call)
- To use it in `Qt` you must encapsulate it within a `QApplication`, see `examples/qt`
- Notebooks plots have ipywidget-based toolbars and widgets 😄

### Desktop examples using `glfw` or `Qt`

GLFW examples are here. GLFW is a "minimal" desktop framework.

https://github.com/fastplotlib/fastplotlib/tree/main/examples/desktop

Qt examples are here:

https://github.com/fastplotlib/fastplotlib/tree/main/examples/qt

Some of the examples require imageio:
```
pip install imageio
```

### Notebook examples

Notebook examples are here:

https://github.com/fastplotlib/fastplotlib/tree/main/examples/notebooks

**Start with `simple.ipynb`.**

Some of the examples require imageio:
```
pip install imageio
```

### Video

Our SciPy 2023 talk walks through numerous demos: https://github.com/fastplotlib/fastplotlib#scipy-talk

## Graphics drivers

You will need a relatively modern GPU (newer integrated GPUs in CPUs are usually fine). Generally if your GPU is from 2017 or later it should be fine.

For more information see: https://wgpu-py.readthedocs.io/en/stable/start.html#platform-requirements

### Windows:
Vulkan drivers should be installed by default on Windows 11, but you will need to install your GPU manufacturer's driver package (Nvidia or AMD). If you have an integrated GPU within your CPU, you might still need to install a driver package too, check your CPU manufacturer's info.

### Linux:
You will generally need a linux distro that is from ~2020 or newer (ex. Ubuntu 18.04 won't work), this is due to the `glibc` requirements of the `wgpu-native` binary.

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
WGPU uses Metal instead of Vulkan on Mac. You will need at least Mac OSX 10.13. The OS should come with Metal pre-installed so you should be good to go!

# :heart: Contributing

We welcome contributions! See the contributing guide: https://github.com/kushalkolar/fastplotlib/blob/main/CONTRIBUTING.md

You can also take a look at our [**Roadmap for 2024**](https://github.com/kushalkolar/fastplotlib/issues/55) and [**Issues**](https://github.com/kushalkolar/fastplotlib/issues) for ideas on how to contribute!
