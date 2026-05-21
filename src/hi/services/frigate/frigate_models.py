from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


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
    # Frigate emits ``has_clip``/``has_snapshot`` booleans per event
    # so the UI can avoid offering playback for events whose clip
    # never made it to disk. Default ``True`` matches Frigate's own
    # default behavior (events come with clips unless explicitly
    # disabled).
    has_clip        : bool                 = True
    has_snapshot    : bool                 = True

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
            has_clip = bool( api_dict.get( 'has_clip', True )),
            has_snapshot = bool( api_dict.get( 'has_snapshot', True )),
        )

    @staticmethod
    def _epoch_to_datetime( epoch_secs : float ) -> datetime:
        return datetime.fromtimestamp( float( epoch_secs ), tz = timezone.utc )


@dataclass
class TrackedFrigateEvent:
    """A Frigate event the monitor is actively tracking — i.e. seen
    open and not yet observed closed.

    ``first_observed_at`` is captured in HI's clock (not Frigate's
    ``start_time``) so the force-close timeout sidesteps any clock
    skew between the two systems. ``event`` snapshots the payload as
    last seen — it's refreshed on each per-id poll until the event
    closes (``end_time`` set) or is force-closed."""

    event              : FrigateEvent
    first_observed_at  : datetime
