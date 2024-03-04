from pathlib import Path

from wgpu.backends.wgpu_native import enumerate_adapters
from wgpu.utils import get_default_device

try:
    ip = get_ipython()
    from ipywidgets import Image
    from wgpu.gui.jupyter import JupyterWgpuCanvas
except (NameError, ModuleNotFoundError, ImportError):
    NOTEBOOK = False
else:
    from IPython.display import display

    if ip.has_trait("kernel") and (JupyterWgpuCanvas is not False):
        NOTEBOOK = True
    else:
        NOTEBOOK = False


def _notebook_print_banner():
    if NOTEBOOK is False:
        return

    logo_path = Path(__file__).parent.parent.joinpath(
        "assets", "fastplotlib_face_logo.png"
    )

    with open(logo_path, "rb") as f:
        logo_data = f.read()

    image = Image(value=logo_data, format="png", width=300, height=55)

    display(image)

    # print logo and adapter info
    adapters = [a for a in enumerate_adapters()]
    adapters_info = [a.request_adapter_info() for a in adapters]

    ix_default = adapters_info.index(
        get_default_device().adapter.request_adapter_info()
    )

    if len(adapters) > 0:
        print("Available devices:")

    for ix, adapter in enumerate(adapters_info):
        atype = adapter["adapter_type"]
        backend = adapter["backend_type"]
        driver = adapter["description"]
        device = adapter["device"]

        if atype == "DiscreteGPU" and backend != "OpenGL":
            charactor = chr(0x2705)
        elif atype == "IntegratedGPU" and backend != "OpenGL":
            charactor = chr(0x0001FBC4)
        else:
            charactor = chr(0x2757)

        if ix == ix_default:
            default = " (default) "
        else:
            default = " "

        output_str = f"{charactor}{default}| {device} | {atype} | {backend} | {driver}"
        print(output_str)
