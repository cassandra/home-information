"""Frigate simulator sim-model definitions.

Scaffolding stub. Feature work introduces the camera + event field
dataclasses + the per-class ``SimEntityDefinition`` registrations the
ServiceSimulator dispatches on. See
``src/hi/simulator/services/zoneminder/sim_models.py`` for the
reference shape (server + monitor + states).
"""
from typing import List

from hi.simulator.services.base_models import SimEntityDefinition


# Empty for now; feature work populates with the FrigateCamera (and
# FrigateServer, if needed) definitions plus their associated state
# classes (motion, object presence, detect on/off).
FRIGATE_SIM_ENTITY_DEFINITION_LIST: List[ SimEntityDefinition ] = []
