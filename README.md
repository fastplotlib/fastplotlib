<p align="center">
<img src="https://github.com/fastplotlib/fastplotlib/blob/main/docs/source/fastplotlib_logo.svg" height="220" alt="logo">
</p>

---

[![CI](https://github.com/fastplotlib/fastplotlib/actions/workflows/ci.yml/badge.svg)](https://github.com/fastplotlib/fastplotlib/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/fastplotlib.svg)](https://badge.fury.io/py/fastplotlib)
[![Deploy docs](https://github.com/fastplotlib/fastplotlib/actions/workflows/docs-deploy.yml/badge.svg)](https://fastplotlib.org/ver/dev/)
[![DOI](https://zenodo.org/badge/485481453.svg)](https://zenodo.org/doi/10.5281/zenodo.13365890)

[**Installation**](https://github.com/fastplotlib/fastplotlib#installation) | 
[**GPU Drivers**](https://github.com/kushalkolar/fastplotlib#graphics-drivers) | 
[**Documentation**](https://github.com/fastplotlib/fastplotlib#documentation) | 
[**Examples**](https://github.com/kushalkolar/fastplotlib#examples) | 
[**Contributing**](https://github.com/kushalkolar/fastplotlib#heart-contributing)

Next-gen plotting library built using the [`pygfx`](https://github.com/pygfx/pygfx) rendering engine that utilizes [Vulkan](https://en.wikipedia.org/wiki/Vulkan), [DX12](https://en.wikipedia.org/wiki/DirectX#DirectX_12), or [Metal](https://developer.apple.com/metal/) via WGPU, so it is very fast! `fastplotlib` is an expressive plotting library that enables rapid prototyping for large scale exploratory scientific visualization.

<div align="center">
  <img src=https://github.com/user-attachments/assets/5c6bede6-e0cb-4867-bb9b-f86cc5e98619 width="1000" /> 
</div>

> **Note:**
> `fastplotlib` is currently in the **late alpha stage**, but you're welcome to use it or contribute! See our [Roadmap](https://github.com/kushalkolar/fastplotlib/issues/55). Also, see this for a discussion on API stability: https://github.com/fastplotlib/fastplotlib/issues/121

# What are *some* things I can do with `fastplotlib`?

- GPU-accelerated visualization

- interactive visualization via an intuitive and expressive API

- rapid prototyping and algorithm design

- easy exploration and fast rendering of large-scale data

- design, develop, evaluate, and ship machine learning models

- create visualizations for real-time acquisition systems for scientific instruments (cameras, etc.)

# Supported frameworks

`fastplotlib` can run on anything that [`pygfx`](https://github.com/pygfx/pygfx) can also run, this includes:

:heavy_check_mark: `Jupyter lab`, using [`jupyter_rfb`](https://github.com/vispy/jupyter_rfb)\
:heavy_check_mark: `PyQt` and `PySide`\
:heavy_check_mark: `glfw`\
:heavy_check_mark: `wxPython`

Write your code once and run it anywhere. Whether you are using `Qt`, `glfw`, `jupyter lab`, or doing offscreen rendering, `fastplotlib` works across all major platforms (Linux, Windows, Mac OS X) :smile: See the [FAQ](https://www.fastplotlib.org/ver/dev/user_guide/faq.html) for more details on where and how you can use `fastplotlib`.

# Documentation

http://www.fastplotlib.org/ver/dev

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

# to use in jupyterlab without imgui
pip install -U "fastplotlib[notebook]"
```

We strongly recommend installing ``simplejpeg`` for use in notebooks, you must first install [libjpeg-turbo](https://libjpeg-turbo.org/)

- If you use ``conda``, you can get ``libjpeg-turbo`` through conda.
- If you are on linux, you can get it through your distro's package manager.
- For Windows and Mac compiled binaries are available on their release page: https://github.com/libjpeg-turbo/libjpeg-turbo/releases

Once you have ``libjpeg-turbo``:

```bash
pip install simplejpeg
```

> **Note:**
> `fastplotlib` and `pygfx` are fast evolving projects, the version available through pip might be outdated, you will need to follow the "For developers" instructions below if you want the latest features. You can find the release history here: https://github.com/fastplotlib/fastplotlib/releases

### For developers

Make sure you have [git-lfs](https://github.com/git-lfs/git-lfs#installing) installed.

```bash
git clone https://github.com/fastplotlib/fastplotlib.git
cd fastplotlib

# install all extras in place
pip install -e ".[notebook,docs,tests,imgui]"

# install latest pygfx
pip install git+https://github.com/pygfx/pygfx.git@main
```

See [Contributing](https://github.com/fastplotlib/fastplotlib?tab=readme-ov-file#heart-contributing) for more details on development

# Examples

Examples gallery: http://fastplotlib.org/ver/dev/_gallery/index.html

User guide: http://fastplotlib.org/ver/dev/user_guide/guide.html

`fastplotlib` code is identical across notebook (`jupyterlab`), and desktop use with `Qt`/`PySide` or `glfw`. 

**Notebooks**

The `quickstart.ipynb` tutorial notebook is a great way to get familiar with the API: https://github.com/fastplotlib/fastplotlib/tree/main/examples/notebooks/quickstart.ipynb

# GPU drivers and requirements

Generally if your GPU is from 2017 or later it should be fine. Modern integrated graphics are usually fine for many use cases. The exact requirements will depend on how complex your visualization is and how many objects you need to render.

More detailed information on GPUs and drivers is here: http://fastplotlib.org/ver/dev/user_guide/gpu.html

For more detailed information, such as use on cloud computing infrastructure, see the WGPU docs: https://wgpu-py.readthedocs.io/en/stable/start.html#cloud-compute

# Contributing :heart:

We welcome contributions! See the contributing guide: https://github.com/fastplotlib/fastplotlib/blob/main/CONTRIBUTING.md

You can also take a look at our [**Roadmap for 2025**](https://github.com/fastplotlib/fastplotlib/issues/55) and [**Issues**](https://github.com/fastplotlib/fastplotlib/issues) for ideas on how to contribute!

# Developers :brain:

- [**Kushal Kolar**](https://github.com/kushalkolar)

- [**Caitlin Lewis**](https://github.com/clewis7)

- [**Almar Klein**](https://github.com/almarklein)

- [**Amol Pasarkar**](https://github.com/apasarkar)

A special thanks to all of the `pygfx` developers and the amazing work they have done. 
