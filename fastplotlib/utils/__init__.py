# this MUST be imported as early as possible in fpl.__init__ before any other wgpu stuff
from .gui import loop
from .enums import *
from .functions import *
from ._config import global_config, ConfigValue
from .gpu import enumerate_adapters, select_adapter, print_wgpu_report
from .protocols import ARRAY_LIKE_ATTRS, ArrayProtocol, FutureProtocol, CudaArrayProtocol
