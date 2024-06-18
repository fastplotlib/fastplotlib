GPU Info and selection
**********************

FAQ
===

1. Do I need a GPU?

Technically no, you can perform limited software rendering on linux using lavapipe (see drivers link below). However
``fastplotlib`` is intentionally built for realtime rendering using the latest GPU technologies, so we strongly
recommend that you use a GPU.

2. My kernel keeps crashing.

This can happen under the following circumstances:

- You have ran out of GPU VRAM.
- Driver issues (see next section).

If you aren't able to solve it please post an issue on GitHub. :)

3. Nothing renders or rendering is weird, or I see graphical artifacts.

- Probably driver issues (see next section).

Drivers
=======

See the README: https://github.com/fastplotlib/fastplotlib?tab=readme-ov-file#graphics-drivers

If you notice weird graphic artifacts, things not rendering, or other glitches try updating to the latest stable
drivers.

GPU Info
========

View available adapters
-----------------------

You can get a summary of all adapters that are available to ``WGPU`` like this::

    import fastplotlib as fpl

    adapters = fpl.enumerate_adapters()

    for a in adapters:
        print(a.summary)

For example, on a Thinkpad AMD laptop with a dedicated nvidia GPU this returns::

    AMD Radeon Graphics (RADV REMBRANDT) (IntegratedGPU) on Vulkan
    NVIDIA T1200 Laptop GPU (DiscreteGPU) on Vulkan
    llvmpipe (LLVM 15.0.6, 256 bits) (CPU) on Vulkan
    AMD Radeon Graphics (rembrandt, LLVM 15.0.6, DRM 3.52, 6.4.0-0.deb12.2-amd64) (Unknown) on OpenGL

In jupyter all the available adapters are also listed when ``fastplotlib`` is imported.

You can get more detailed info on each adapter like this::

    import pprint
    for a in fpl.enumerate_adapters():
        pprint.pprint(a.info)

General description of the fields:
    * vendor: GPU manufacturer
    * device: specific GPU model
    * description: GPU driver version
    * adapter_type: indicates whether this is a discrete GPU, integrated GPU, or software rendering adapter (CPU)
    * backend_type: one of "Vulkan", "Metal", or "D3D12"

For more information on the fields see: https://gpuweb.github.io/gpuweb/#gpuadapterinfo

Adapter currently in use
------------------------

If you want to know the adapter that a figure is using you can check the adapter on the renderer::

    # for example if we make a plot
    fig = fpl.Figure()
    fig[0, 0].add_image(np.random.rand(100, 100))
    fig.show()

    # GPU that is currently in use by the renderer
    print(fig.renderer.device.adapter.summary)


Diagnostic info
---------------

After creating a figure you can view WGPU diagnostic info like this::

    fpl.print_wgpu_report()


Example output::

    ██ system:

                 platform:  Linux-5.10.0-21-amd64-x86_64-with-glibc2.31
    python_implementation:  CPython
                   python:  3.11.3

    ██ versions:

           wgpu:  0.15.1
           cffi:  1.15.1
    jupyter_rfb:  0.4.2
          numpy:  1.26.4
          pygfx:  0.2.0
       pylinalg:  0.4.1
    fastplotlib:  0.1.0.a16

    ██ wgpu_native_info:

    expected_version:  0.19.3.1
         lib_version:  0.19.3.1
            lib_path:  ./resources/libwgpu_native-release.so

    ██ object_counts:

                          count  resource_mem

                Adapter:      1
              BindGroup:      3
        BindGroupLayout:      3
                 Buffer:      6           696
          CanvasContext:      1
          CommandBuffer:      0
         CommandEncoder:      0
     ComputePassEncoder:      0
        ComputePipeline:      0
                 Device:      1
         PipelineLayout:      0
               QuerySet:      0
                  Queue:      1
           RenderBundle:      0
    RenderBundleEncoder:      0
      RenderPassEncoder:      0
         RenderPipeline:      3
                Sampler:      2
           ShaderModule:      3
                Texture:      6         9.60M
            TextureView:      6

                  total:     36         9.60M

    ██ wgpu_native_counts:

                      count    mem  backend   a  k  r  e  el_size

            Adapter:      1  1.98K   vulkan:  1  1  3  0    1.98K
          BindGroup:      3  1.10K   vulkan:  3  3  0  0      368
    BindGroupLayout:      3    960   vulkan:  5  3  2  0      320
             Buffer:      6  1.77K   vulkan:  7  6  1  0      296
      CanvasContext:      0      0            0  0  0  0      160
      CommandBuffer:      1  1.25K   vulkan:  0  0  0  1    1.25K
    ComputePipeline:      0      0   vulkan:  0  0  0  0      288
             Device:      1  11.8K   vulkan:  1  1  0  0    11.8K
     PipelineLayout:      0      0   vulkan:  3  0  3  0      200
           QuerySet:      0      0   vulkan:  0  0  0  0       80
              Queue:      1    184   vulkan:  1  1  0  0      184
       RenderBundle:      0      0   vulkan:  0  0  0  0      848
     RenderPipeline:      3  1.68K   vulkan:  3  3  0  0      560
            Sampler:      2    160   vulkan:  2  2  0  0       80
       ShaderModule:      3  2.40K   vulkan:  3  3  0  0      800
            Texture:      6  4.94K   vulkan:  7  6  1  0      824
        TextureView:      6  1.48K   vulkan:  6  6  1  0      248

              total:     36  29.7K

        * The a, k, r, e are allocated, kept, released, and error, respectively.
        * Reported memory does not include buffer/texture data.

    ██ pygfx_adapter_info:

          vendor:  radv
    architecture:
          device:  AMD RADV POLARIS10 (ACO)
     description:  Mesa 20.3.5 (ACO)
       vendor_id:  4.09K
       device_id:  26.5K
    adapter_type:  DiscreteGPU
    backend_type:  Vulkan

    ██ pygfx_features:

                                           adapter  device

                      bgra8unorm-storage:        -       -
                   depth32float-stencil8:        ✓       -
                      depth-clip-control:        ✓       -
                      float32-filterable:        ✓       ✓
                 indirect-first-instance:        ✓       -
                rg11b10ufloat-renderable:        ✓       -
                              shader-f16:        -       -
                texture-compression-astc:        -       -
                  texture-compression-bc:        ✓       -
                texture-compression-etc2:        -       -
                         timestamp-query:        ✓       -
                       MultiDrawIndirect:        ✓       -
                  MultiDrawIndirectCount:        ✓       -
                           PushConstants:        ✓       -
    TextureAdapterSpecificFormatFeatures:        ✓       -
                   VertexWritableStorage:        ✓       -

    ██ pygfx_limits:

                                                      adapter  device

                                    max_bind_groups:        8       8
                max_bind_groups_plus_vertex_buffers:        0       0
                        max_bindings_per_bind_group:    1.00K   1.00K
                                    max_buffer_size:    2.14G   2.14G
              max_color_attachment_bytes_per_sample:        0       0
                              max_color_attachments:        0       0
              max_compute_invocations_per_workgroup:    1.02K   1.02K
                       max_compute_workgroup_size_x:    1.02K   1.02K
                       max_compute_workgroup_size_y:    1.02K   1.02K
                       max_compute_workgroup_size_z:    1.02K   1.02K
                 max_compute_workgroup_storage_size:    32.7K   32.7K
               max_compute_workgroups_per_dimension:    65.5K   65.5K
    max_dynamic_storage_buffers_per_pipeline_layout:        8       8
    max_dynamic_uniform_buffers_per_pipeline_layout:       16      16
                  max_inter_stage_shader_components:      128     128
                   max_inter_stage_shader_variables:        0       0
              max_sampled_textures_per_shader_stage:    8.38M   8.38M
                      max_samplers_per_shader_stage:    8.38M   8.38M
                    max_storage_buffer_binding_size:    2.14G   2.14G
               max_storage_buffers_per_shader_stage:    8.38M   8.38M
              max_storage_textures_per_shader_stage:    8.38M   8.38M
                           max_texture_array_layers:    2.04K   2.04K
                            max_texture_dimension1d:    16.3K   16.3K
                            max_texture_dimension2d:    16.3K   16.3K
                            max_texture_dimension3d:    2.04K   2.04K
                    max_uniform_buffer_binding_size:    2.14G   2.14G
               max_uniform_buffers_per_shader_stage:    8.38M   8.38M
                              max_vertex_attributes:       32      32
                     max_vertex_buffer_array_stride:    2.04K   2.04K
                                 max_vertex_buffers:       16      16
                min_storage_buffer_offset_alignment:       32      32
                min_uniform_buffer_offset_alignment:       32      32

    ██ pygfx_caches:

                        count  hits  misses

    full_quad_objects:      1     0       2
     mipmap_pipelines:      0     0       0
              layouts:      1     0       3
             bindings:      1     0       1
       shader_modules:      2     0       2
            pipelines:      2     0       2
     shadow_pipelines:      0     0       0

    ██ pygfx_resources:

    Texture:  8
     Buffer:  23


Select GPU (adapter)
====================

You can select an adapter by passing one of the ``wgpu.GPUAdapter`` instances returned by ``fpl.enumerate_adapters()``
to ``fpl.select_adapter()``::

    # get info or summary of all adapters to pick an adapter
    import pprint
    for a in fpl.enumerate_adapters():
        pprint.pprint(a.info)

    # example, pick adapter at index 2
    chosen_gpu = fpl.enumerate_adapters()[2]
    fpl.select_adapter(chosen_gpu)

**You must select an adapter before creating a** ``Figure`` **, otherwise the default adapter will be selected. Once a**
``Figure`` **is created the adapter cannot be changed.**

Note that using this function reduces the portability of your code, because
it's highly specific for your current machine/environment.

The order of the adapters returned by ``wgpu.gpu.enumerate_adapters()`` is
such that Vulkan adapters go first, then Metal, then D3D12, then OpenGL.
Within each category, the order as provided by the particular backend is
maintained. Note that the same device may be present via multiple backends
(e.g. vulkan/opengl).

We cannot make guarantees about whether the order of the adapters matches
the order as reported by e.g. ``nvidia-smi``. We have found that on a Linux
multi-gpu cluster, the order does match, but we cannot promise that this is
always the case. If you want to make sure, do some testing by allocating big
buffers and checking memory usage using ``nvidia-smi``

Example to allocate and check GPU mem usage::

    import subprocess

    import wgpu
    import torch

    def allocate_gpu_mem_with_wgpu(idx):
        a = wgpu.gpu.enumerate_adapters()[idx]
        d = a.request_device()
        b = d.create_buffer(size=10*2**20, usage=wgpu.BufferUsage.COPY_DST)
        return b

    def allocate_gpu_mem_with_torch(idx):
        d = torch.device(f"cuda:{idx}")
        return torch.ones([2000, 10], dtype=torch.float32, device=d)

    def show_mem_usage():
        print(subprocess.run(["nvidia-smi"]))

See https://github.com/pygfx/wgpu-py/issues/482 for more details.
