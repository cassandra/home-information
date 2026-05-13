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
    observation's value did not match)."""

    value               : str
    timestamp           : datetime
    entity_state        : EntityState
    instrument          : Instrument
    history_value_type  : StateHistoryValueType
    matched_intent      : Optional[ MatchedIntent ] = None


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
