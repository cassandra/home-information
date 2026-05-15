"""
Map HealthStatusProvider state transitions to system alarms.

Stateless policy concentrator. Inputs: a HealthStatusTransition plus the
provider's declared maximum allowed alarm level. Output: an Optional[Alarm]
that the caller (HealthStatusProvider._dispatch_transition_alarm) hands to
AlertManager.

Design echoes WeatherAlertAlarmMapper:
- Single create_alarm() entry point; helper methods are pure.
- Alarms apply at SecurityLevel.OFF (universal — health affects everyone).
- Distinct alarm_type strings for error vs recovery so the alert queue
  treats them as separate alerts the user can see and acknowledge
  independently.

Per-provider seriousness is expressed as a maximum alarm level (the
"ceiling"), declared by the provider via HealthStatusProvider.alarm_ceiling.
The mapper picks a "natural" alarm level for the transition class
(ERROR=CRITICAL, WARNING=WARNING, recovery=INFO) and clamps to the
provider's ceiling. This lets each provider declare relative importance
(e.g., HASS/ZM ceiling=CRITICAL, HomeBox ceiling=INFO) without owning the
full mapping policy.

Transitions involving UNKNOWN or DISABLED on either side are
suppressed entirely (no alarm fires). UNKNOWN is initialization noise
with no settled baseline; DISABLED is operator-initiated and the
operator already knows.
"""
from typing import List, Optional
import logging

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.alert.alarm import Alarm
from hi.apps.alert.enums import AlarmLevel, AlarmSource
from hi.apps.security.enums import SecurityLevel
from hi.apps.sense.transient_models import SensorResponse
from hi.integrations.transient_models import IntegrationKey

from .enums import HealthStatusType
from .health_status_transition import HealthStatusTransition

logger = logging.getLogger(__name__)


class HealthStatusAlarmMapper:

    # Single shared lifetime for both error and recovery alarms. They
    # MUST match: if recovery expired before the error it's resolving,
    # the user would be left looking at a bare error alert from the
    # moment the recovery disappeared until the error finally expired —
    # incorrectly suggesting the integration is still broken.
    ALARM_LIFETIME_SECS = 30 * 60

    # Natural alarm level for each transition class, BEFORE the
    # per-provider ceiling is applied. DISABLED is intentionally
    # omitted — see _ALARM_SUPPRESSED_STATES.
    NATURAL_LEVEL_FOR_NEW_STATUS = {
        HealthStatusType.ERROR    : AlarmLevel.CRITICAL,
        HealthStatusType.WARNING  : AlarmLevel.WARNING,
    }
    RECOVERY_NATURAL_LEVEL = AlarmLevel.INFO

    # States whose presence on EITHER side of a transition disqualifies
    # the transition from alarming:
    #   UNKNOWN  - initialization edge; no settled baseline to compare
    #              against.
    #   DISABLED - operator-initiated; entering it is the operator's
    #              explicit action and exiting it is the operator's
    #              explicit re-enable. The operator already knows; an
    #              alarm would be a redundant confirmation.
    _ALARM_SUPPRESSED_STATES = frozenset({
        HealthStatusType.UNKNOWN,
        HealthStatusType.DISABLED,
    })

    def should_create_alarm( self, transition : HealthStatusTransition ) -> bool:
        if ( transition.previous_status in self._ALARM_SUPPRESSED_STATES
             or transition.current_status in self._ALARM_SUPPRESSED_STATES ):
            return False

        # Recovery: HEALTHY from a non-HEALTHY state.
        if transition.is_recovery:
            return True

        # Forward transitions into states that warrant an alarm.
        if transition.current_status in self.NATURAL_LEVEL_FOR_NEW_STATUS:
            return True

        return False

    def get_alarm_level( self,
                         transition  : HealthStatusTransition,
                         max_level   : AlarmLevel ) -> Optional[ AlarmLevel ]:
        if not self.should_create_alarm( transition ):
            return None

        if transition.is_recovery:
            natural = self.RECOVERY_NATURAL_LEVEL
        else:
            natural = self.NATURAL_LEVEL_FOR_NEW_STATUS.get( transition.current_status )
        if natural is None:
            return None

        # Clamp to the provider's declared ceiling.
        if natural.priority > max_level.priority:
            return max_level
        return natural

    def get_alarm_lifetime_secs( self, transition : HealthStatusTransition ) -> int:
        return self.ALARM_LIFETIME_SECS

    def get_alarm_type( self, transition : HealthStatusTransition ) -> str:
        # Distinct types so error and recovery produce separate alerts
        # the user can see and acknowledge independently. Includes the
        # provider id so signatures group sensibly when multiple
        # providers are unhealthy at once.
        provider_id = transition.provider_info.provider_id
        if transition.is_recovery:
            return f'health_status.{provider_id}.recovered'
        return f'health_status.{provider_id}.error'

    def get_alarm_title( self, transition : HealthStatusTransition ) -> str:
        provider_name = transition.provider_info.provider_name
        if transition.is_recovery:
            return f'{provider_name} recovered'
        return f'{provider_name} unhealthy'

    def create_sensor_responses( self,
                                 transition : HealthStatusTransition ) -> List[ SensorResponse ]:
        provider_info = transition.provider_info
        detail_attrs = {
            'Provider'         : provider_info.provider_name,
            'Status'           : transition.current_status.label,
            'Previous Status'  : transition.previous_status.label,
            'Error Count'      : str( transition.error_count ),
            'Last Update'      : transition.timestamp.strftime( '%Y-%m-%d %H:%M:%S' ),
        }
        if transition.last_message:
            message = transition.last_message
            if len( message ) > 300:
                message = message[ :300 ] + '...'
            detail_attrs[ 'Message' ] = message

        # Synthetic integration_key — health-status alarms don't have a
        # backing sensor record, but downstream rendering treats this
        # field as the canonical pointer to the alarm's source.
        integration_key = IntegrationKey(
            integration_id = 'health_status',
            integration_name = provider_info.provider_id,
        )
        return [
            SensorResponse(
                integration_key = integration_key,
                value = transition.current_status.name,
                timestamp = transition.timestamp,
                sensor = None,
                detail_attrs = detail_attrs,
                source_image_url = None,
                has_video_stream = False,
            ),
        ]

    def create_alarm( self,
                      transition  : HealthStatusTransition,
                      max_level   : AlarmLevel ) -> Optional[ Alarm ]:
        alarm_level = self.get_alarm_level( transition = transition, max_level = max_level )
        if alarm_level is None:
            return None

        alarm = Alarm(
            alarm_source = AlarmSource.HEALTH_STATUS,
            alarm_type = self.get_alarm_type( transition = transition ),
            alarm_level = alarm_level,
            title = self.get_alarm_title( transition = transition ),
            sensor_response_list = self.create_sensor_responses( transition = transition ),
            security_level = SecurityLevel.OFF,
            alarm_lifetime_secs = self.get_alarm_lifetime_secs( transition = transition ),
            timestamp = datetimeproxy.now(),
        )
        logger.info( f'Created health-status alarm: {alarm.signature} - {alarm.title}' )
        return alarm
