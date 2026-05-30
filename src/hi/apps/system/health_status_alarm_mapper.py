"""
Map HealthStatusProvider state transitions to system alarms.

Stateless policy concentrator. Inputs: a HealthStatusTransition plus the
provider's declared maximum allowed alarm level. Output for a degrade
transition: an Optional[Alarm] the caller hands to AlertManager. Output
for a recovery transition: an Optional[AlarmSignature] the caller hands
to AlertManager.clear_alarms so the prior bad-state alert drops from
the queue.

- Single create_alarm() entry point for degrades; helper methods are pure.
- Alarms apply at SecurityLevel.OFF (universal -- health affects everyone).

Per-provider seriousness is expressed as a maximum alarm level (the
"ceiling"), declared by the provider via HealthStatusProvider.alarm_ceiling.
The mapper picks a "natural" alarm level for the transition class
(ERROR=CRITICAL, WARNING=WARNING) and clamps to the provider's ceiling.
The recovery-target helper applies the SAME clamp, so the level it
returns matches the level the error alarm was queued at.

Transitions involving UNKNOWN or DISABLED on either side are
suppressed entirely (no alarm fires, no recovery target). UNKNOWN is
initialization noise with no settled baseline; DISABLED is
operator-initiated and the operator already knows.
"""
from typing import List, Optional
import logging

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.alert.alarm import Alarm, AlarmSignature
from hi.apps.alert.enums import AlarmLevel, AlarmSource
from hi.apps.security.enums import SecurityLevel
from hi.apps.sense.transient_models import SensorResponse
from hi.integrations.transient_models import IntegrationKey

from .enums import HealthStatusType
from .health_status_transition import HealthStatusTransition

logger = logging.getLogger(__name__)


class HealthStatusAlarmMapper:

    ALARM_LIFETIME_SECS = 30 * 60

    # Natural alarm level for each transition class, BEFORE the
    # per-provider ceiling is applied. DISABLED is intentionally
    # omitted -- see _ALARM_SUPPRESSED_STATES.
    NATURAL_LEVEL_FOR_NEW_STATUS = {
        HealthStatusType.ERROR    : AlarmLevel.CRITICAL,
        HealthStatusType.WARNING  : AlarmLevel.WARNING,
    }

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

    @staticmethod
    def _error_alarm_type( provider_id : str ) -> str:
        # Shared by the degrade (queue) and recovery (clear-target)
        # paths; recovery clears the alarm an earlier degrade queued,
        # so the two paths MUST agree on the type string.
        return f'health_status.{provider_id}.error'

    def should_create_alarm( self, transition : HealthStatusTransition ) -> bool:
        # Recovery transitions are handled by the clear-target path.
        if transition.is_recovery:
            return False
        if ( transition.previous_status in self._ALARM_SUPPRESSED_STATES
             or transition.current_status in self._ALARM_SUPPRESSED_STATES ):
            return False
        if transition.current_status in self.NATURAL_LEVEL_FOR_NEW_STATUS:
            return True

        return False

    def _natural_level_for_bad_status(
            self,
            status     : HealthStatusType,
            max_level  : AlarmLevel ) -> Optional[ AlarmLevel ]:
        # The clamped alarm level a forward (degrade) transition INTO
        # ``status`` would fire at -- shared by ``get_alarm_level`` and
        # ``get_recovery_target_signature`` so the two paths produce
        # identical levels for the same (status, ceiling) pair.
        natural = self.NATURAL_LEVEL_FOR_NEW_STATUS.get( status )
        if natural is None:
            return None
        if natural.priority > max_level.priority:
            return max_level
        return natural

    def get_alarm_level( self,
                         transition  : HealthStatusTransition,
                         max_level   : AlarmLevel ) -> Optional[ AlarmLevel ]:
        if not self.should_create_alarm( transition ):
            return None
        return self._natural_level_for_bad_status(
            status    = transition.current_status,
            max_level = max_level,
        )

    def get_recovery_target_signature(
            self,
            transition  : HealthStatusTransition,
            max_level   : AlarmLevel,
    ) -> Optional[ AlarmSignature ]:
        """For a recovery transition, return the ``AlarmSignature`` the
        prior bad-state alarm was queued under. Caller hands this to
        ``AlertManager.clear_alarms`` to drop that alert from the queue.

        Returns ``None`` for:
        - Non-recovery transitions (caller has nothing to clear).
        - Recoveries from a state the mapper would have suppressed
          (UNKNOWN, DISABLED) -- no prior alarm was issued, so nothing
          to clear."""
        if not transition.is_recovery:
            return None
        previous_status = transition.previous_status
        if previous_status in self._ALARM_SUPPRESSED_STATES:
            return None
        level = self._natural_level_for_bad_status(
            status    = previous_status,
            max_level = max_level,
        )
        if level is None:
            return None
        return AlarmSignature(
            alarm_source = AlarmSource.HEALTH_STATUS,
            alarm_type   = self._error_alarm_type( transition.provider_info.provider_id ),
            alarm_level  = level,
        )

    def get_alarm_lifetime_secs( self, transition : HealthStatusTransition ) -> int:
        return self.ALARM_LIFETIME_SECS

    def get_alarm_type( self, transition : HealthStatusTransition ) -> str:
        return self._error_alarm_type( transition.provider_info.provider_id )

    def get_alarm_title( self, transition : HealthStatusTransition ) -> str:
        return f'{transition.provider_info.provider_name} unhealthy'

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
                has_event_video_clip = False,
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
