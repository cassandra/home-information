from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class FrigateEvent:
    """Wraps a single Frigate ``/api/events`` JSON record.

    Frigate's event lifecycle (``new`` / ``update`` / ``end``) maps
    onto HI's MOVEMENT correlation pattern the same way ZoneMinder's
    event records do — see ``ZmEvent`` for the reference shape.
    Scaffolding stub; fields filled in during feature work.
    """
    event_id        : str
    camera_name     : str
    object_class    : str
    score           : Optional[ float ] = None
    start_datetime  : Optional[ datetime ] = None
    end_datetime    : Optional[ datetime ] = None
    sub_label       : Optional[ str ] = None
    zones           : Optional[ List[ str ] ] = None
    snapshot_url    : Optional[ str ] = None
    clip_url        : Optional[ str ] = None

    @property
    def is_open(self) -> bool:
        return self.end_datetime is None

    @property
    def is_closed(self) -> bool:
        return self.end_datetime is not None
