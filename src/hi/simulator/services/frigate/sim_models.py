"""Frigate simulator sim-model definitions.

The simulator emits raw Frigate-style object class labels
(``person``, ``car``, ``dog``, ...) — exactly what a real Frigate
instance would publish. The HI-side ``FrigateConverter`` buckets
these onto the canonical ``OBJECT_PRESENCE`` value range. Including
a deliberately uncategorized label (``unicorn``) in the operator's
choice list keeps the ``other`` bucket on the demo path.
"""
from dataclasses import dataclass
from typing import ClassVar, List, Tuple

from hi.apps.common.utils import str_to_bool

from hi.simulator.services.base_models import (
    SimEntityDefinition,
    SimEntityFields,
    SimState,
)
from hi.simulator.services.enums import SimEntityType, SimStateType
from hi.simulator.services.sim_entity import SimEntity


@dataclass( frozen = True )
class FrigateCameraSimEntityFields( SimEntityFields ):
    """Operator-configurable fields for a simulated Frigate camera.

    ``camera_name`` is the per-camera identifier used in Frigate's
    URL paths (``/api/<camera_name>/latest.jpg``) and as the
    ``camera`` field on events. Mirrors Frigate's own config-file
    naming (``cameras:`` map keyed by name)."""

    name         : str  = 'Frigate Camera'
    camera_name  : str  = 'sim_camera_1'


# Raw Frigate-style object labels presented to the operator on the
# ObjectPresence discrete control. Includes one deliberately
# uncategorized label so the ``other`` bucket on the HI side
# remains exercisable.
FRIGATE_OBJECT_LABEL_CHOICES: List[ Tuple[ str, str ] ] = [
    ( 'none', 'No Object' ),
    ( 'person', 'Person' ),
    ( 'car', 'Car' ),
    ( 'truck', 'Truck' ),
    ( 'dog', 'Dog' ),
    ( 'cat', 'Cat' ),
    ( 'package', 'Package' ),
    ( 'unicorn', 'Unicorn (unmapped)' ),
]
FRIGATE_OBJECT_LABEL_NONE = 'none'


@dataclass
class FrigateCameraMotionState( SimState ):
    """ON/OFF motion flag for the camera. Toggling this in the
    simulator UI is what synthesizes Frigate-shape events (see the
    forthcoming ``FrigateSimEventManager`` in step D1)."""

    sim_entity_fields  : FrigateCameraSimEntityFields
    sim_state_type     : SimStateType                  = SimStateType.MOVEMENT
    sim_state_id       : str                           = 'motion'

    @property
    def name(self):
        return 'Camera Motion'

    def set_value_from_string( self, value_str : str ):
        self.value = str_to_bool( value_str )
        return


@dataclass
class FrigateCameraObjectPresenceState( SimState ):
    """Currently-detected object class. Discrete enum whose value
    space carries raw Frigate-side labels; the HI converter buckets
    those onto the canonical ``OBJECT_PRESENCE`` set
    (``person`` / ``car`` / ``animal`` / ``package`` / ``other`` /
    ``none``)."""

    OBJECT_PRESENCE_SIM_STATE_ID : ClassVar[ str ] = 'object_presence'

    sim_entity_fields  : FrigateCameraSimEntityFields
    sim_state_type     : SimStateType                  = SimStateType.DISCRETE
    sim_state_id       : str                           = OBJECT_PRESENCE_SIM_STATE_ID
    value              : str                           = FRIGATE_OBJECT_LABEL_NONE

    @property
    def name(self):
        return 'Detected Object'

    @property
    def choices(self) -> List[ Tuple[ str, str ] ]:
        return FRIGATE_OBJECT_LABEL_CHOICES


@dataclass( frozen = True )
class FrigateSimCamera:
    """Per-entity accessor wrapper for a simulated Frigate camera.

    Mirrors ``ZmSimMonitor`` in role: convenient typed property
    access onto a single camera ``SimEntity`` so views / event
    managers don't reach into ``sim_entity_fields`` / ``sim_state_list``
    directly. Pure projection — no behavior beyond reads."""

    sim_entity  : SimEntity

    @property
    def camera_name(self) -> str:
        return self.sim_entity.sim_entity_fields.camera_name

    @property
    def display_name(self) -> str:
        return self.sim_entity.sim_entity_fields.name

    @property
    def motion_sim_state(self) -> FrigateCameraMotionState:
        for sim_state in self.sim_entity.sim_state_list:
            if isinstance( sim_state, FrigateCameraMotionState ):
                return sim_state
            continue
        raise ValueError( f'No motion sim state for Frigate camera {self.sim_entity}' )

    @property
    def object_presence_sim_state(self) -> FrigateCameraObjectPresenceState:
        for sim_state in self.sim_entity.sim_state_list:
            if isinstance( sim_state, FrigateCameraObjectPresenceState ):
                return sim_state
            continue
        raise ValueError(
            f'No object-presence sim state for Frigate camera {self.sim_entity}'
        )


FRIGATE_SIM_ENTITY_DEFINITION_LIST: List[ SimEntityDefinition ] = [
    SimEntityDefinition(
        class_label = 'Camera',
        sim_entity_type = SimEntityType.CAMERA,
        sim_entity_fields_class = FrigateCameraSimEntityFields,
        sim_state_class_list = [
            FrigateCameraMotionState,
            FrigateCameraObjectPresenceState,
        ],
    ),
]
