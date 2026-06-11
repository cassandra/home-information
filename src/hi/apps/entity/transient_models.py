from dataclasses import dataclass, field
from typing import Any, Dict, List

from hi.apps.entity.edit.forms import EntityPositionForm

from .entity_state_history import EntityStateHistoryValue
from .enums import EntityGroupType, EntityPairingType, VideoStreamType
from .forms import EntityForm
from .models import Entity, EntityState


@dataclass
class VideoStream:
    """Represents a video stream from any source"""
    stream_type: VideoStreamType
    source_url: str = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Future extensibility:
    # webrtc_config: WebRTCConfig = None
    # hls_manifest_url: str = None
    # thumbnail_url: str = None


@dataclass
class VideoSnapshot:
    """A still image of a camera's current view, fetched on demand.

    Parallel to ``VideoStream`` but distinct because the two capabilities
    are orthogonal: an entity can provide a stream, a snapshot, both, or
    neither. Integrations declare what they natively provide via the
    corresponding gateway methods (``get_entity_video_stream`` /
    ``get_entity_video_snapshot``); higher-level synthesis (e.g.,
    presenting a snapshot-only camera as a low-rate refresh "stream"
    for display) is a separate concern that consumes both capabilities.

    Naming note: "video_snapshot" is used (rather than bare "snapshot")
    to disambiguate from the existing ZoneMinder event-snapshot
    terminology (a frame extracted from a past recorded event)."""
    source_url: str = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EntityViewItem:

    entity          : Entity
    exists_in_view  : bool
    is_unused       : bool = False

    
@dataclass
class EntityViewGroup:
    """All entities of a given type and flagged as in the view or not."""

    entity_group_type  : EntityGroupType
    item_list          : List[EntityViewItem]  = field( default_factory = list )


@dataclass
class LocationViewEntityPickerData:
    """The two sections of the LocationView item picker, built together
    from a single entity scan: the type-grouped non-delegate entities and
    the flat delegate ("Paired Items") list."""

    entity_view_group_list   : List[EntityViewGroup]  = field( default_factory = list )
    delegate_view_item_list  : List[EntityViewItem]   = field( default_factory = list )

    
@dataclass
class EntityPairing:
    """
    An "Entity Pair: abstracts the concepts of principal and delegate
    entities to a simpler, non-directional view for end users.  We only
    allow an entity to participate as a principal or a delegate, not
    both. Further, We only allow a primcipal entity to delegate if it has
    EntityStates and we do not allow delegates to have their own
    state. Thus, by just pairing two entities, we can deduce which
    direction the delagation relatiojnship goes.
    """
    entity         : Entity
    paired_entity  : Entity
    pairing_type   : EntityPairingType
    

@dataclass
class EntityEditModeData:
    """
    All the data needed about an entity to display in side bar during edit
    mode.
    """

    entity                : Entity
    entity_form           : EntityForm             = None
    entity_position_form  : EntityPositionForm     = None
    entity_pairing_list   : List[ EntityPairing ]  = None

    def __post_init__(self):
        if not self.entity_form:
            self.entity_form = EntityForm(
                instance = self.entity,
            )

    def to_template_context(self):
        return {
            'entity': self.entity,
            'entity_form': self.entity_form,
            'entity_position_form': self.entity_position_form,
            'entity_pairing_list': self.entity_pairing_list,
        }

    
@dataclass
class EntityHistoryData:

    entity         : Entity
    state_to_rows  : Dict[ EntityState, List[ EntityStateHistoryValue ] ]

    def to_template_context(self):
        return {
            'entity': self.entity,
            'state_to_rows': self.state_to_rows,
        }

