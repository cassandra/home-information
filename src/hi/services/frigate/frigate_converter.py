import logging
from typing import Optional

from hi.apps.entity.enums import EntityStateValue

from .constants import FrigateApi

logger = logging.getLogger(__name__)


class FrigateConverter:
    """Wire-format ↔ HI model translation for Frigate.

    Owns the boundary between Frigate's raw event payloads and HI's
    typed model. Responsibilities:

    - Map Frigate's raw object-class label (model-dependent — default
      YOLO has ~80 classes; custom models can have arbitrary classes)
      onto the canonical ``EntityStateType.OBJECT_PRESENCE`` value
      range.
    - Map HI's outbound on/off controller value to Frigate's detect
      state vocabulary. Explicit dict lookup; no string transforms
      (HI's lowercase ``on`` and Frigate's uppercase ``ON`` are
      independent vocabularies that coincidentally rhyme).
    """

    # Raw-label → canonical-bucket map. Entries are lowercase-canonical
    # Frigate class names paired with the matching EntityStateValue
    # member. Anything not listed falls through to ``OBJECT_OTHER``;
    # this is deliberate so a custom-model class that nobody's bucketed
    # yet still surfaces in HI as "something is here" rather than
    # disappearing into ``none``.
    _RAW_TO_CANONICAL = {
        # People
        'person'      : EntityStateValue.OBJECT_PERSON,

        # Vehicles. ``OBJECT_CAR`` is the canonical bucket name but
        # semantically it's "vehicle" — trucks, buses, etc. all map
        # here. Rename of the bucket is a UX decision worth revisiting
        # if/when other vehicle-aware integrations land.
        'car'         : EntityStateValue.OBJECT_CAR,
        'truck'       : EntityStateValue.OBJECT_CAR,
        'bus'         : EntityStateValue.OBJECT_CAR,
        'motorcycle'  : EntityStateValue.OBJECT_CAR,
        'bicycle'     : EntityStateValue.OBJECT_CAR,

        # Animals — covers the COCO classes most likely to fire in
        # a residential install plus the common custom additions.
        'dog'         : EntityStateValue.OBJECT_ANIMAL,
        'cat'         : EntityStateValue.OBJECT_ANIMAL,
        'bird'        : EntityStateValue.OBJECT_ANIMAL,
        'horse'       : EntityStateValue.OBJECT_ANIMAL,
        'sheep'       : EntityStateValue.OBJECT_ANIMAL,
        'cow'         : EntityStateValue.OBJECT_ANIMAL,
        'bear'        : EntityStateValue.OBJECT_ANIMAL,
        'deer'        : EntityStateValue.OBJECT_ANIMAL,
        'raccoon'     : EntityStateValue.OBJECT_ANIMAL,
        'fox'         : EntityStateValue.OBJECT_ANIMAL,
        'squirrel'    : EntityStateValue.OBJECT_ANIMAL,
        'rabbit'      : EntityStateValue.OBJECT_ANIMAL,

        # Packages — Frigate's dedicated class for porch deliveries.
        'package'     : EntityStateValue.OBJECT_PACKAGE,
    }

    OBJECT_NONE_VALUE = str( EntityStateValue.OBJECT_NONE )
    OBJECT_OTHER_VALUE = str( EntityStateValue.OBJECT_OTHER )

    @classmethod
    def to_canonical_object_class( cls, raw_class : str ) -> str:
        """Map a Frigate raw object class onto a canonical
        ``OBJECT_PRESENCE`` value (the wire-format string of the
        matching ``EntityStateValue`` member). Unknown labels fall
        through to ``OBJECT_OTHER`` so detections of custom-model
        classes still register in HI."""
        if not raw_class:
            return cls.OBJECT_OTHER_VALUE
        canonical = cls._RAW_TO_CANONICAL.get( raw_class.lower() )
        if canonical is None:
            return cls.OBJECT_OTHER_VALUE
        return str( canonical )

    # HI controller value (lowercase, per LabeledEnum.__str__) →
    # Frigate detect-state wire value. Independent vocabularies.
    _HI_CONTROL_TO_DETECT_STATE = {
        str( EntityStateValue.ON ): FrigateApi.DETECT_STATE_ON,
        str( EntityStateValue.OFF ): FrigateApi.DETECT_STATE_OFF,
    }

    @classmethod
    def hi_control_to_detect_state( cls, hi_control_value : str ) -> Optional[ str ]:
        """Map an HI on/off controller value to the Frigate detect
        state string. Returns ``None`` for unknown input so the
        controller can surface a clean error to the operator rather
        than firing a malformed POST at Frigate."""
        return cls._HI_CONTROL_TO_DETECT_STATE.get( hi_control_value )

    # Inbound mapping: Frigate ``/api/config`` carries ``cameras.<n>.
    # detect.enabled`` as a bool. Translate to HI's wire value via
    # explicit lookup so the polling path never produces an
    # off-vocabulary string.
    _DETECT_ENABLED_TO_HI_VALUE = {
        True: str( EntityStateValue.ON ),
        False: str( EntityStateValue.OFF ),
    }

    @classmethod
    def detect_enabled_to_hi_value( cls, detect_enabled : bool ) -> str:
        """Map a Frigate detect-enabled flag to the HI on/off value."""
        return cls._DETECT_ENABLED_TO_HI_VALUE[ bool( detect_enabled ) ]
