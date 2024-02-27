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

    from wgpu.backends.wgpu_native import enumerate_adapters
    from pprint import pprint

    for adapter in enumerate_adapters():
        pprint(adapter.request_adapter_info())

For example, on a Thinkpad AMD laptop with a dedicated nvidia GPU this returns::

    {'adapter_type': 'IntegratedGPU',
     'architecture': '',
     'backend_type': 'Vulkan',
     'description': 'Mesa 22.3.6',
     'device': 'AMD Radeon Graphics (RADV REMBRANDT)',
     'vendor': 'radv'}
    {'adapter_type': 'DiscreteGPU',
     'architecture': '',
     'backend_type': 'Vulkan',
     'description': '535.129.03',
     'device': 'NVIDIA T1200 Laptop GPU',
     'vendor': 'NVIDIA'}
    {'adapter_type': 'CPU',
     'architecture': '',
     'backend_type': 'Vulkan',
     'description': 'Mesa 22.3.6 (LLVM 15.0.6)',
     'device': 'llvmpipe (LLVM 15.0.6, 256 bits)',
     'vendor': 'llvmpipe'}
    {'adapter_type': 'Unknown',
     'architecture': '',
     'backend_type': 'OpenGL',
     'description': '',
     'device': 'AMD Radeon Graphics (rembrandt, LLVM 15.0.6, DRM 3.52, '
               '6.4.0-0.deb12.2-amd64)',
     'vendor': ''}

GPU currently in use
--------------------

If you want to know the GPU that a current plot is using you can check the adapter that the renderer is using::

    # for example if we make a plot
    plot = fpl.Plot()
    plot.add_image(np.random.rand(100, 100))
    plot.show()

    # GPU that is currently in use by the renderer
    plot.renderer.device.adapter.request_adapter_info()

