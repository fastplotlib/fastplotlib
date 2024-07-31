from dataclasses import dataclass


from .functions import *
from .gpu import enumerate_adapters, select_adapter, print_wgpu_report
from ._plot_helpers import *


@dataclass
class _Config:
    party_parrot: bool


config = _Config(party_parrot=False)
