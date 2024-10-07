from dataclasses import dataclass

from .gui import run  # this MUST be imported as early as possible in fpl.__init__ before any other wgpu stuff
from .functions import *
from .gpu import enumerate_adapters, select_adapter, print_wgpu_report
from ._plot_helpers import *


@dataclass
class _Config:
    party_parrot: bool


config = _Config(party_parrot=False)
