from dataclasses import dataclass


from .functions import *


@dataclass
class _Config:
    party_parrot: bool


config = _Config(party_parrot=False)
