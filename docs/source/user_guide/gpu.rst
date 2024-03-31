GPU Info
********

FAQ
---

1. Do I need a GPU?

Technically no, you can perform limited software rendering on linux using lavapipe (see drivers link below). However
``fastplotlib`` is intentionally built for realtime rendering using the latest GPU technologies, so we strongly
recommend that you use a GPU.

2. My kernel keeps crashing when I create visualizations.

This can happen under the following circumstances:

- You have ran out of GPU VRAM.
- Driver issues (see next section).

If you aren't able to solve it please post an issue on GitHub. :)

Drivers
-------

See the README: https://github.com/fastplotlib/fastplotlib?tab=readme-ov-file#graphics-drivers

If you notice weird graphic artifacts, things not rendering, or other glitches try updating to the latest stable
drivers.


View available GPU
------------------

You can view all GPUs that are available to ``WGPU`` like this::

    import wgpu

    for adapter in wgpu.gpu.enumerate_adapters():
        print(adapter.summary)

For example, on a Thinkpad AMD laptop with a dedicated nvidia GPU this returns::

    AMD Radeon Graphics (RADV REMBRANDT) (IntegratedGPU) on Vulkan
    NVIDIA T1200 Laptop GPU (DiscreteGPU) on Vulkan
    llvmpipe (LLVM 15.0.6, 256 bits) (CPU) on Vulkan
    AMD Radeon Graphics (rembrandt, LLVM 15.0.6, DRM 3.52, 6.4.0-0.deb12.2-amd64) (Unknown) on OpenGL


GPU currently in use
--------------------

If you want to know the GPU that a current plot is using you can check the adapter that the renderer is using::

    # for example if we make a plot
    plot = fpl.Plot()
    plot.add_image(np.random.rand(100, 100))
    plot.show()

    # GPU that is currently in use by the renderer
    print(plot.renderer.device.adapter.summary)

