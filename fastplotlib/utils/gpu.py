import wgpu
from pygfx.renderers.wgpu import select_adapter as pygfx_select_adapter
from pygfx import print_wgpu_report as pygfx_print_wgpu_report


def enumerate_adapters() -> list[wgpu.GPUAdapter]:
    return wgpu.gpu.enumerate_adapters_sync()


enumerate_adapters.__doc__ = wgpu.gpu.enumerate_adapters_async.__doc__


def select_adapter(adapter: wgpu.GPUAdapter):
    return pygfx_select_adapter(adapter)


select_adapter.__doc__ = pygfx_select_adapter.__doc__


def print_wgpu_report():
    return pygfx_print_wgpu_report()


print_wgpu_report.__doc__ = pygfx_print_wgpu_report.__doc__
