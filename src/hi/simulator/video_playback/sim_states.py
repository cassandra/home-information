"""Platform-neutral camera sim_states for pre-canned footage.

A camera's live feed and event feed each select a clip by name. These are plain
DISCRETE sim_states (choices from the ``VideoClipManager`` pool, default
``synthetic`` = today's placeholder), so they record/replay in a scenario like
any other state. Shared by the Frigate and ZoneMinder camera definitions so the
two platforms expose an identical clip-selection control.
"""
from dataclasses import dataclass
from typing import ClassVar, List, Tuple

from hi.simulator.services.base_models import SimEntityFields, SimState
from hi.simulator.services.enums import SimStateType

from .video_clip_manager import SYNTHETIC_CLIP_VALUE, VideoClipManager


@dataclass
class CameraLiveClipState( SimState ):
    """Pre-canned clip backing a camera's live feed."""

    LIVE_CLIP_SIM_STATE_ID : ClassVar[ str ] = 'live_clip'

    sim_entity_fields  : SimEntityFields
    sim_state_type     : SimStateType         = SimStateType.DISCRETE
    sim_state_id       : str                  = LIVE_CLIP_SIM_STATE_ID
    value              : str                  = SYNTHETIC_CLIP_VALUE

    @property
    def name(self):
        return 'Live Clip'

    @property
    def choices(self) -> List[ Tuple[ str, str ] ]:
        return VideoClipManager().get_clip_choices()


@dataclass
class CameraEventClipState( SimState ):
    """Pre-canned clip backing a camera's event snapshot/clip. Separate from the
    live clip so a scenario can show the live scene and a matching event feed
    independently."""

    EVENT_CLIP_SIM_STATE_ID : ClassVar[ str ] = 'event_clip'

    sim_entity_fields  : SimEntityFields
    sim_state_type     : SimStateType         = SimStateType.DISCRETE
    sim_state_id       : str                  = EVENT_CLIP_SIM_STATE_ID
    value              : str                  = SYNTHETIC_CLIP_VALUE

    @property
    def name(self):
        return 'Event Clip'

    @property
    def choices(self) -> List[ Tuple[ str, str ] ]:
        return VideoClipManager().get_clip_choices()
