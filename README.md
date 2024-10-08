<p align="center">
<img src="https://github.com/fastplotlib/fastplotlib/blob/main/docs/source/fastplotlib_logo.svg" height="220" alt="logo">
</p>

---

[![CI](https://github.com/fastplotlib/fastplotlib/actions/workflows/ci.yml/badge.svg)](https://github.com/fastplotlib/fastplotlib/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/fastplotlib.svg)](https://badge.fury.io/py/fastplotlib)
[![Documentation Status](https://readthedocs.org/projects/fastplotlib/badge/?version=latest)](https://fastplotlib.readthedocs.io/en/latest/?badge=latest)
[![DOI](https://zenodo.org/badge/485481453.svg)](https://zenodo.org/doi/10.5281/zenodo.13365890)

[**Installation**](https://github.com/fastplotlib/fastplotlib#installation) | 
[**GPU Drivers**](https://github.com/kushalkolar/fastplotlib#graphics-drivers) | 
[**Documentation**](https://github.com/fastplotlib/fastplotlib#documentation) | 
[**Examples**](https://github.com/kushalkolar/fastplotlib#examples) | 
[**Contributing**](https://github.com/kushalkolar/fastplotlib#heart-contributing)

Next-gen plotting library built using the [`pygfx`](https://github.com/pygfx/pygfx) rendering engine that can utilize [Vulkan](https://en.wikipedia.org/wiki/Vulkan), [DX12](https://en.wikipedia.org/wiki/DirectX#DirectX_12), or [Metal](https://developer.apple.com/metal/) via WGPU, so it is very fast! `fastplotlib` is an expressive plotting library that enables rapid prototyping for large scale explorative scientific visualization.

> **Note**
> 
> `fastplotlib` is currently in the **late alpha stage**, but you're welcome to try it out or contribute! See our [Roadmap](https://github.com/kushalkolar/fastplotlib/issues/55). See this for a discussion on API stability: https://github.com/fastplotlib/fastplotlib/issues/121

# Supported frameworks

`fastplotlib` can run on anything that [`pygfx`](https://github.com/pygfx/pygfx) can also run, this includes:

:heavy_check_mark: `Jupyter lab`, using [`jupyter_rfb`](https://github.com/vispy/jupyter_rfb)\
:heavy_check_mark: `PyQt` and `PySide`\
:heavy_check_mark: `glfw`\
:heavy_check_mark: `wxPython`

**Notes:**\
:heavy_check_mark: Non-blocking interactive Qt/PySide output is supported in ipython and notebooks, see http://fastplotlib.org/ver/dev/user_guide/guide.html#using-fastplotlib-in-an-interactive-shell \
:grey_exclamation: We do not officially support `jupyter notebook` through `jupyter_rfb`, this may change with notebook v7\
:grey_exclamation: We only officially support jupyterlab for use in notebook. This means we do not support vscode notebooks etc. Jupyterlab is the most reliable way to use `fastplotlib` in notebooks.\
:disappointed: [`jupyter_rfb`](https://github.com/vispy/jupyter_rfb) does not work in collab, see https://github.com/vispy/jupyter_rfb/pull/77 

We recommend sticking to jupyter-lab for notebooks. From our experience the usage on other platforms, such as vscode 
notebooks, is not optimal. 


# Documentation

http://www.fastplotlib.org/

Questions, issues, ideas? You are welcome to post an [issue](https://github.com/fastplotlib/fastplotlib/issues) or post on the [discussion forum](https://github.com/fastplotlib/fastplotlib/discussions)! :smiley: 

# Installation

To install use pip:

```bash
# with imgui and jupyterlab
pip install -U "fastplotlib[notebook,imgui]"

# minimal install, install glfw, pyqt6 or pyside6 separately
pip install -U fastplotlib

# with imgui
pip install -U "fastplotlib[imgui]"

# to use in jupyterlab, no imgui
pip install -U "fastplotlib[notebook]"
```

We strongly recommend installing ``simplejpeg`` for use in notebooks, you must first install [libjpeg-turbo](https://libjpeg-turbo.org/)

- If you use ``conda``, you can get ``libjpeg-turbo`` through conda.
- If you are on linux you can get it through your distro's package manager.
- For Windows and Mac compiled binaries are available on their release page: https://github.com/libjpeg-turbo/libjpeg-turbo/releases

Once you have ``libjpeg-turbo``:

```bash
pip install simplejpeg
```

> **Note**[guide.rst](docs%2Fsource%2Fuser_guide%2Fguide.rst)
>
> `fastplotlib` and `pygfx` are fast evolving projects, the version available through pip might be outdated, you will need to follow the "For developers" instructions below if you want the latest features. You can find the release history here: https://github.com/fastplotlib/fastplotlib/releases

### For developers

Make sure you have [git-lfs](https://github.com/git-lfs/git-lfs#installing) installed.

```bash
git clone https://github.com/fastplotlib/fastplotlib.git
cd fastplotlib

# install all extras in place
pip install -e ".[notebook,docs,tests]"

# install latest pygfx
pip install git+https://github.com/pygfx/pygfx.git@main
```

Se [Contributing](https://github.com/fastplotlib/fastplotlib?tab=readme-ov-file#heart-contributing) for more details on development

# Examples

Examples gallery: http://fastplotlib.org/ver/dev/_gallery/index.html

User guide: http://fastplotlib.org/ver/dev/user_guide/guide.html

`fastplotlib` code is identical across notebook (`jupyterlab`), and desktop use with `Qt`/`PySide` or `glfw`. 

**Notebooks**

The `quickstart.ipynb` tutorial notebook is a great way to get familiar with the API: https://github.com/fastplotlib/fastplotlib/tree/main/examples/notebooks/quickstart.ipynb

## Graphics drivers

You will need a relatively modern GPU, modern integrated graphics are usually fine for many use cases. Generally if your GPU is from 2017 or later it should be fine.

For more detailed information, such as use on cloud computing infrastructure, see: https://wgpu-py.readthedocs.io/en/stable/start.html#platform-requirements

Some more information on GPUs is here: http://fastplotlib.org/ver/dev/user_guide/gpu.html

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
WGPU uses Metal instead of Vulkan on Mac. You will need at least Mac OSX 10.13. The OS should come with Metal pre-installed, so you should be good to go!

# :heart: Contributing

We welcome contributions! See the contributing guide: https://github.com/fastplotlib/fastplotlib/blob/main/CONTRIBUTING.md

You can also take a look at our [**Roadmap for 2025**](https://github.com/fastplotlib/fastplotlib/issues/55) and [**Issues**](https://github.com/fastplotlib/fastplotlib/issues) for ideas on how to contribute!
