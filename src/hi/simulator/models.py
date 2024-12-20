from dataclasses import dataclass
from typing import List

from .enums import SimEntityStateType


@dataclass
class SimEntity:

    entity_id        : str
    name             : str
    state_type       : SimEntityStateType
    state_value      : str


@dataclass
class SimDevice:

    device_id        : str
    name             : str
    sim_entity_list  : List[ SimEntity ]

