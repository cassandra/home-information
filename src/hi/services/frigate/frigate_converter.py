import logging

logger = logging.getLogger(__name__)


class FrigateConverter:
    """Wire-format ↔ HI model translation for Frigate.

    Owns the boundary between Frigate's raw event/camera payloads and
    HI's Entity / EntityState / SensorResponse model. Two main jobs in
    feature work:

    1. **Inbound** — translate a ``/api/events`` JSON record into a
       ``FrigateEvent`` plus a HI ``SensorResponse`` for each affected
       EntityState. Includes mapping Frigate's raw object class
       (model-dependent) onto the canonical
       ``EntityStateType.OBJECT_PRESENCE`` value range
       (``person`` / ``car`` / ``animal`` / ``package`` / ``other`` /
       ``none``).

    2. **Outbound** — translate a HI control value (e.g., flipping a
       camera's Detect On/Off controller) into the corresponding
       Frigate API call.

    Scaffolding stub. Methods raise ``NotImplementedError`` until
    feature work fills them in.
    """

    # Canonical OBJECT_PRESENCE value range. Frigate's raw class set
    # is model-dependent; anything that doesn't map to one of these
    # buckets into ``other``. Kept here (not on the EntityStateType
    # enum) because the mapping is integration-specific — different
    # camera/NVR integrations may bucket differently.
    OBJECT_PRESENCE_CANONICAL_VALUES = (
        'person',
        'car',
        'animal',
        'package',
        'other',
        'none',
    )

    @classmethod
    def to_canonical_object_class( cls, raw_class : str ) -> str:
        """Map a Frigate raw object class onto the canonical
        OBJECT_PRESENCE value range. Scaffolding stub returns
        ``other`` for everything; feature work fills in the table."""
        return 'other'
