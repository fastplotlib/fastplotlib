from dataclasses import dataclass

# this MUST be imported as early as possible in fpl.__init__ before any other wgpu stuff
from .gui import loop
from .enums import *
from .functions import *
from .gpu import enumerate_adapters, select_adapter, print_wgpu_report
from ._plot_helpers import *
from .protocols import ARRAY_LIKE_ATTRS, ArrayProtocol, FutureProtocol, CudaArrayProtocol


@dataclass
class _Config:
    party_parrot: bool


config = _Config(party_parrot=False)
