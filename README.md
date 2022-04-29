# fastplotlib
A fast plotting library built using the pygfx render engine which uses Vulkan instead of OpenGL, so it is very fast!

Checkout pygfx!
https://github.com/pygfx/pygfx

fastplotlib is very experimental, you're welcome to try it out or contribute!

# Installation

You will need a GPU that supports Vulkan (iGPUs in CPUs should be fine). 
Generally if your GPU is from 2017 or later it should support Vulkan.

## Install Vulkan drivers

For more information see: https://github.com/pygfx/wgpu-py#platform-requirements

### Windows:
Apparently Vulkan should be installed by default on Windows 11.

### Linux:
Debian based distros:

```bash
sudo apt install mesa-vulkan-drivers
```

For other distros use Google to find the appropriate vulkan driver package

### Mac OSX:
You will need at least MacOSX v10.13
 

```commandline
pip install https://github.com/kushalkolar/fastplotlib.git
```

### Very fast image updates

https://user-images.githubusercontent.com/9403332/165678225-dcf3b401-86a5-4df5-a9e5-dc65bdb0443a.mp4

### Scatter plot

https://user-images.githubusercontent.com/9403332/165677576-a0aa2d0f-a201-4e0e-91bd-aed800f775ee.mp4

### Lineplot

https://user-images.githubusercontent.com/9403332/165678270-aea65a83-6cc1-4edc-981c-4857eaf293c7.mp4

