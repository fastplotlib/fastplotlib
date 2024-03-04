from dataclasses import dataclass


from .functions import *
from ._gpu_info import _notebook_print_banner


@dataclass
class _Config:
    party_parrot: bool


config = _Config(party_parrot=False)
