"""Frigate simulator sim-model definitions.

The simulator emits raw Frigate-style object class labels
(``person``, ``car``, ``dog``, ...) — exactly what a real Frigate
instance would publish. The HI-side ``FrigateConverter`` buckets
these onto the canonical ``OBJECT_PRESENCE`` value range. Including
a deliberately uncategorized label (``unicorn``) in the operator's
choice list keeps the ``other`` bucket on the demo path.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar, List, Optional, Tuple

import hi.apps.common.datetimeproxy as datetimeproxy

from hi.simulator.services.base_models import (
    SimEntityDefinition,
    SimEntityFields,
    SimState,
)
from hi.simulator.services.enums import SimEntityType, SimStateType
from hi.simulator.services.sim_entity import SimEntity
from hi.simulator.video_playback.sim_states import (
    CameraEventClipState,
    CameraLiveClipState,
)
from hi.simulator.video_playback.video_clip_manager import SYNTHETIC_CLIP_VALUE


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
class FrigateCameraObjectPresenceState( SimState ):
    """Currently-detected object class — the SINGLE per-camera state
    the simulator exposes. Frigate's data model couples motion to
    object detection (no motion-without-class signal on the events
    API), so this discrete state is the only control the operator
    needs: pick the raw class to declare "this is what's currently
    being detected"; pick ``none`` to declare "nothing is detected".

    The HI-side ``FrigateConverter`` buckets the raw label onto the
    canonical ``OBJECT_PRESENCE`` set
    (``person`` / ``car`` / ``animal`` / ``package`` / ``other`` /
    ``none``). The simulator's ``set_sim_state`` override translates
    value changes into the underlying event lifecycle (open / close /
    swap), so the operator never has to manage motion + label as
    separate controls.
    """

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
    def object_presence_sim_state(self) -> FrigateCameraObjectPresenceState:
        for sim_state in self.sim_entity.sim_state_list:
            if isinstance( sim_state, FrigateCameraObjectPresenceState ):
                return sim_state
            continue
        raise ValueError(
            f'No object-presence sim state for Frigate camera {self.sim_entity}'
        )

    @property
    def live_clip(self) -> str:
        return self._clip_value( CameraLiveClipState )

    @property
    def event_clip(self) -> str:
        return self._clip_value( CameraEventClipState )

    def _clip_value(self, sim_state_class) -> str:
        for sim_state in self.sim_entity.sim_state_list:
            if isinstance( sim_state, sim_state_class ):
                return sim_state.value
            continue
        return SYNTHETIC_CLIP_VALUE


@dataclass
class FrigateSimEvent:
    """One synthesized Frigate event, tracked in memory by
    ``FrigateSimEventHistory``.

    ``label`` is the raw Frigate-side object class (e.g. ``person``,
    ``dog``) — the same value space the camera's ObjectPresence
    sim-state carries. ``start_datetime`` / ``end_datetime`` follow
    Frigate's event lifecycle: ``end_datetime is None`` means the
    event is still open. ``score`` is a generated placeholder for v1;
    real Frigate emits a 0..1 best-score-so-far per event."""

    event_id        : str
    camera_name     : str
    label           : str
    start_datetime  : datetime
    end_datetime    : Optional[ datetime ] = None
    score           : float                = 0.85

    @property
    def is_active(self) -> bool:
        return self.end_datetime is None

    @property
    def is_open(self) -> bool:
        return self.end_datetime is None

    @property
    def is_closed(self) -> bool:
        return self.end_datetime is not None

    def close( self ) -> None:
        if self.end_datetime is None:
            self.end_datetime = datetimeproxy.now()
        return

    def to_api_dict(self) -> dict:
        """Frigate-shape ``/api/events`` JSON for one event. Field set
        is the subset HI's integration cares about plus a few real
        Frigate fields kept so the response is recognizable. Times
        are epoch seconds (Frigate's wire convention)."""
        end_epoch = self.end_datetime.timestamp() if self.end_datetime else None
        return {
            'id': self.event_id,
            'camera': self.camera_name,
            'label': self.label,
            'sub_label': None,
            'start_time': self.start_datetime.timestamp(),
            'end_time': end_epoch,
            'top_score': self.score,
            'false_positive': False,
            'zones': [],
            'thumbnail': None,
            'has_clip': True,
            'has_snapshot': True,
        }


FRIGATE_SIM_ENTITY_DEFINITION_LIST: List[ SimEntityDefinition ] = [
    SimEntityDefinition(
        class_label = 'Camera',
        sim_entity_type = SimEntityType.CAMERA,
        sim_entity_fields_class = FrigateCameraSimEntityFields,
        sim_state_class_list = [
            FrigateCameraObjectPresenceState,
            CameraLiveClipState,
            CameraEventClipState,
        ],
    ),
]
