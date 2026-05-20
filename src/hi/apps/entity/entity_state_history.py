"""Per-EntityState merged history: a chronological view of an
EntityState's value over time, combining sensor observations and
controller intents on a single timeline.

An observation that occurs shortly after a controller intent with
the same value absorbs that intent as an annotation. Unmatched
intents (control actions that produced no confirming observation
within the merge window) emit as standalone rows so failed or
yet-to-be-confirmed commands stay visible."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from hi.apps.common.enums import LabeledEnum
from hi.apps.control.models import ControllerHistory
from hi.apps.entity.models import EntityState
from hi.apps.sense.models import SensorHistory
from hi.apps.sense.sensor_history_urls import (
    sensor_history_details_url,
    sensor_history_video_browse_url,
)


# Maximum delay between a controller intent and a subsequent matching
# sensor observation for the two to collapse into a single row.
# Bounds typical polling jitter and the local force-set write HI
# performs at control time.
MERGE_WINDOW_SECONDS = 10


class StateHistoryValueType(LabeledEnum):

    OBSERVATION = ( 'Observation' , '' )
    INTENT      = ( 'Intent'      , '' )


class InstrumentType(LabeledEnum):

    SENSOR     = ( 'Sensor'     , '' )
    CONTROLLER = ( 'Controller' , '' )


@dataclass
class Instrument:
    """Display projection of a history value's source. Carries only
    the fields the merged-history view renders, so the row type
    stays insulated from sensor- vs controller-specific model
    structure."""

    id              : int
    name            : str
    instrument_type : InstrumentType


@dataclass
class MatchedIntent:
    """Annotation on an observation: an HI control action confirmed
    by this reading within the merge window. Its instrument is the
    controller that issued the intent."""

    instrument : Instrument
    timestamp  : datetime


@dataclass
class EntityStateHistoryValue:
    """A row in the per-EntityState merged timeline.

    OBSERVATION rows record what was sensed. ``matched_intent`` is
    set when an HI control action with the same value was confirmed
    by this reading within the merge window.

    INTENT rows record an HI control action that produced no
    confirming observation within the window (or where the
    observation's value did not match).

    Click-through metadata (``sensor_history_id``, ``has_event_video_clip``,
    ``has_details``, ``provides_event_video_clip``) is populated on
    OBSERVATION rows from the underlying ``SensorHistory`` and the
    parent ``Sensor``. INTENT rows leave these at defaults since
    controllers don't have video or details to link to."""

    value                 : str
    timestamp             : datetime
    entity_state          : EntityState
    instrument            : Instrument
    history_value_type    : StateHistoryValueType
    matched_intent        : Optional[ MatchedIntent ] = None
    sensor_history_id     : Optional[ int ]           = None
    has_event_video_clip      : bool                      = False
    has_details           : bool                      = False
    provides_event_video_clip : bool                      = False

    @property
    def video_browse_url(self) -> Optional[ str ]:
        """Click-through to the video event browser for this row.
        OBSERVATION rows route via the sensor; INTENT rows return
        ``None`` (controllers don't have video)."""
        if self.history_value_type != StateHistoryValueType.OBSERVATION:
            return None
        return sensor_history_video_browse_url(
            entity_id = self.entity_state.entity.id,
            sensor_id = self.instrument.id,
            sensor_history_id = self.sensor_history_id,
            has_event_video_clip = self.has_event_video_clip,
            provides_event_video_clip = self.provides_event_video_clip,
        )

    @property
    def details_url(self) -> Optional[ str ]:
        """Click-through to the per-row details modal for this row.
        OBSERVATION rows with detail attributes route to the details
        modal; INTENT rows return ``None``."""
        if self.history_value_type != StateHistoryValueType.OBSERVATION:
            return None
        return sensor_history_details_url(
            sensor_history_id = self.sensor_history_id,
            has_details = self.has_details,
        )

    @property
    def click_url(self) -> Optional[ str ]:
        """Composite: prefers the video URL over the details URL.
        ``None`` when neither applies (e.g., INTENT rows, or
        OBSERVATION rows with no video and no details)."""
        return self.video_browse_url or self.details_url


def get_entity_state_history_page(
        entity_state    : EntityState,
        page_size       : int                = 25,
        before          : Optional[datetime] = None,
        window_seconds  : int                = MERGE_WINDOW_SECONDS,
) -> List[ EntityStateHistoryValue ]:
    """Sensor-anchored page of merged history for ``entity_state``.

    Fetches the ``page_size`` most-recent observations older than
    ``before`` (or most-recent overall if None), then fetches every
    controller intent older than ``before`` and not older than the
    page's oldest observation (minus the merge-window buffer so
    in-window intents at the page's tail can still match).

    Falls back to controller-only when the state has no observations
    in range: returns the ``page_size`` most-recent intents older
    than ``before``.

    Returned rows are descending by timestamp; the caller derives
    the next-page cursor from the oldest row's timestamp."""

    obs_query = SensorHistory.objects.filter( sensor__entity_state = entity_state )
    if before is not None:
        obs_query = obs_query.filter( response_datetime__lt = before )
    observation_rows = list(
        obs_query.order_by( '-response_datetime' )[ : page_size ]
    )

    intent_query = ControllerHistory.objects.filter(
        controller__entity_state = entity_state,
    )
    if before is not None:
        intent_query = intent_query.filter( created_datetime__lt = before )

    if observation_rows:
        t_oldest = min( o.response_datetime for o in observation_rows )
        intent_query = intent_query.filter(
            created_datetime__gte = t_oldest - timedelta( seconds = window_seconds ),
        )
        intent_rows = list( intent_query )
    else:
        intent_rows = list(
            intent_query.order_by( '-created_datetime' )[ : page_size ]
        )

    return merge_history(
        entity_state     = entity_state,
        observation_rows = observation_rows,
        intent_rows      = intent_rows,
        window_seconds   = window_seconds,
    )


def merge_history(
        entity_state      : EntityState,
        observation_rows  : List[ SensorHistory ],
        intent_rows       : List[ ControllerHistory ],
        window_seconds    : int                       = MERGE_WINDOW_SECONDS,
) -> List[ EntityStateHistoryValue ]:
    """Collapse intents and observations into merged rows in
    descending timestamp order.

    Each intent claims the chronologically-earliest unclaimed
    observation that occurs within ``window_seconds`` after it
    (inclusive) and whose stored value matches by exact string
    equality. Claimed observations carry the intent as an
    annotation; unclaimed intents emit standalone."""

    observations_asc = sorted( observation_rows, key = lambda h: h.response_datetime )
    intents_asc = sorted( intent_rows, key = lambda h: h.created_datetime )

    window = timedelta( seconds = window_seconds )
    claimed_obs : Dict[ int, ControllerHistory ] = {}
    unmatched_intents : List[ ControllerHistory ] = []

    for intent in intents_asc:
        matched = False
        for i, obs in enumerate( observations_asc ):
            if i in claimed_obs:
                continue
            if obs.response_datetime < intent.created_datetime:
                continue
            if obs.response_datetime > intent.created_datetime + window:
                # Ascending sort: no later observation can fall in window.
                break
            if obs.value == intent.value:
                claimed_obs[ i ] = intent
                matched = True
                break
            continue
        if not matched:
            unmatched_intents.append( intent )
        continue

    rows : List[ EntityStateHistoryValue ] = []
    for i, obs in enumerate( observations_asc ):
        matched_intent : Optional[ MatchedIntent ] = None
        claim = claimed_obs.get( i )
        if claim is not None:
            matched_intent = MatchedIntent(
                instrument = _controller_instrument( claim ),
                timestamp = claim.created_datetime,
            )
        rows.append( EntityStateHistoryValue(
            value = obs.value,
            timestamp = obs.response_datetime,
            entity_state = entity_state,
            instrument = _sensor_instrument( obs ),
            history_value_type = StateHistoryValueType.OBSERVATION,
            matched_intent = matched_intent,
            sensor_history_id = obs.id,
            has_event_video_clip = obs.has_event_video_clip,
            has_details = bool( obs.detail_attrs ),
            provides_event_video_clip = obs.sensor.provides_event_video_clip,
        ))
        continue
    for intent_history in unmatched_intents:
        rows.append( EntityStateHistoryValue(
            value = intent_history.value,
            timestamp = intent_history.created_datetime,
            entity_state = entity_state,
            instrument = _controller_instrument( intent_history ),
            history_value_type = StateHistoryValueType.INTENT,
            matched_intent = None,
        ))
        continue

    rows.sort( key = lambda r: r.timestamp, reverse = True )
    return rows


def _sensor_instrument( sensor_history : SensorHistory ) -> Instrument:
    sensor = sensor_history.sensor
    return Instrument(
        id = sensor.id,
        name = sensor.name,
        instrument_type = InstrumentType.SENSOR,
    )


def _controller_instrument( controller_history : ControllerHistory ) -> Instrument:
    controller = controller_history.controller
    return Instrument(
        id = controller.id,
        name = controller.name,
        instrument_type = InstrumentType.CONTROLLER,
    )
