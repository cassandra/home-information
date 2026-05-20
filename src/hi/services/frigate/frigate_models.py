from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from hi.apps.entity.enums import EntityStateValue


@dataclass
class FrigateEvent:
    """HI-side wrapper for a single Frigate ``/api/events`` record.

    Frigate's event lifecycle (``new`` / ``update`` / ``end``) maps
    onto HI's MOVEMENT correlation pattern the same way ZoneMinder
    events do — see ``ZmEvent`` for the reference shape. Fields are
    populated by ``from_api_dict``.
    """

    event_id        : str
    camera_name     : str
    object_class    : str
    start_datetime  : datetime
    end_datetime    : Optional[ datetime ] = None
    score           : Optional[ float ]    = None
    sub_label       : Optional[ str ]      = None
    zones           : Optional[ List[ str ] ] = None
    snapshot_url    : Optional[ str ]      = None
    clip_url        : Optional[ str ]      = None

    @property
    def is_open(self) -> bool:
        return self.end_datetime is None

    @property
    def is_closed(self) -> bool:
        return self.end_datetime is not None

    @classmethod
    def from_api_dict( cls, api_dict : Dict[ str, Any ] ) -> 'FrigateEvent':
        """Parse one entry of the ``/api/events`` JSON array.

        Frigate emits start_time / end_time as epoch-seconds floats;
        we hold them as TZ-aware ``datetime`` (UTC) for parity with
        the rest of HI's datetime handling. Missing required fields
        raise ``ValueError``; missing optional fields default to
        ``None``."""
        try:
            event_id = str( api_dict[ 'id' ] )
            camera_name = api_dict[ 'camera' ]
            object_class = api_dict[ 'label' ]
            start_epoch = api_dict[ 'start_time' ]
        except KeyError as e:
            raise ValueError(
                f'Frigate event payload missing required field: {e}'
            ) from e

        start_datetime = cls._epoch_to_datetime( start_epoch )
        end_epoch = api_dict.get( 'end_time' )
        end_datetime = (
            cls._epoch_to_datetime( end_epoch ) if end_epoch is not None else None
        )
        return cls(
            event_id = event_id,
            camera_name = camera_name,
            object_class = object_class,
            start_datetime = start_datetime,
            end_datetime = end_datetime,
            score = api_dict.get( 'top_score' ),
            sub_label = api_dict.get( 'sub_label' ),
            zones = api_dict.get( 'zones' ),
        )

    @staticmethod
    def _epoch_to_datetime( epoch_secs : float ) -> datetime:
        return datetime.fromtimestamp( float( epoch_secs ), tz = timezone.utc )


@dataclass
class AggregatedCameraState:
    """Per-camera aggregation result emitted by the polling pipeline.

    Mirrors ``AggregatedMonitorState`` (ZM): one instance per camera
    that produced events in the current poll window. ``current_state``
    is ACTIVE iff any open event was seen; otherwise IDLE.
    ``effective_timestamp`` reflects when the state took effect — the
    start of the earliest open event for ACTIVE, the end of the
    latest closed event for IDLE — so downstream history reflects
    the correct moment.
    """

    camera_name          : str
    current_state        : EntityStateValue
    effective_timestamp  : datetime
    canonical_event      : FrigateEvent
    all_events           : List[ FrigateEvent ]

    @property
    def is_active(self) -> bool:
        return self.current_state == EntityStateValue.ACTIVE

    @property
    def is_idle(self) -> bool:
        return self.current_state == EntityStateValue.IDLE
