# fastplotlib
[![Gitter](https://badges.gitter.im/fastplotlib/community.svg)](https://gitter.im/fastplotlib/community?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge)

A fast plotting library built using the `pygfx` render engine that can use [Vulkan](https://en.wikipedia.org/wiki/Vulkan), so it is very fast!

Checkout pygfx!
https://github.com/pygfx/pygfx

`fastplotlib` is in the alpha stage and experimental but you're welcome to try it out or contribute!

Questions, ideas? Chat on gitter: https://gitter.im/fastplotlib/community?utm_source=share-link&utm_medium=link&utm_campaign=share-link 

# Examples

**See the examples directory. Start out with `simple.ipynb` which uses the high level API.**

### Simple image plot
```python
from fastplotlib import Plot
import numpy as np

plot = Plot()

data = np.random.rand(512, 512) * 255
plot.image(data=data,  vmin=0, vmax=255, cmap='viridis')

plot.show()
```

### Fast image updates (video)
```python
from fastplotlib import Plot
import numpy as np

plot = Plot()

data = np.random.rand(512, 512) * 255
image = plot.image(data=data,  vmin=0, vmax=255, cmap='viridis')

def update_data():
    new_data = np.random.rand(512, 512) * 255
    image.update_data(new_data)

plot.add_animations([update_data])

plot.show()
```

# Installation

`fastplotlib` is available as a `pip` package

```bash
pip install fastplotlib
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
Apparently Vulkan should be installed by default on Windows 11.

### Linux:
Debian based distros:

```bash
sudo apt install mesa-vulkan-drivers
# for better performance with the remote frame buffer install libjpeg-turbo
sudo apt install libjpeg-turbo
```

For other distros install the appropriate vulkan driver package.

### Mac OSX:
You will need at least MacOSX v10.13, not sure how to install Vulkan drivers on Mac. If anyone knows you can add instructions here!

# Gallery

### Extremely fast image updates, 5 x 5 gridplot

https://www.youtube.com/embed/-_0Gp_EqepI

### Very fast image updates with some synced controllers

https://user-images.githubusercontent.com/9403332/165678225-dcf3b401-86a5-4df5-a9e5-dc65bdb0443a.mp4

### Scatter plot

https://user-images.githubusercontent.com/9403332/165677576-a0aa2d0f-a201-4e0e-91bd-aed800f775ee.mp4

### Lineplot

https://user-images.githubusercontent.com/9403332/165678270-aea65a83-6cc1-4edc-981c-4857eaf293c7.mp4

