"""
Convert weather alerts (using canonical WeatherEventType) into system alarms.

Mapping inputs: event type significance (life-threatening vs informational),
alert severity, alert status (actual vs test/exercise), urgency, and certainty.
"""
import logging
from typing import List, Optional

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.alert.alarm import Alarm
from hi.apps.alert.enums import AlarmLevel, AlarmSource
from hi.apps.security.enums import SecurityLevel
from hi.apps.sense.transient_models import SensorResponse
from hi.apps.weather.enums import AlertSeverity, AlertStatus, AlertUrgency, WeatherEventType
from hi.apps.weather.transient_models import WeatherAlert
from hi.integrations.transient_models import IntegrationKey

logger = logging.getLogger(__name__)


class WeatherAlertAlarmMapper:
    """
    Maps weather alerts to system alarms using canonical event types.
    
    Design principles:
    1. Life-threatening events always create alarms regardless of severity
    2. Severity mapping is conservative to prevent alert fatigue
    3. Alarm lifetimes reflect urgency and typical duration of conditions
    4. Weather alarms apply to all security levels (weather affects everyone)
    5. Test/exercise alerts are excluded from alarm creation
    """
    
    # Weather event types that should ALWAYS create alarms (life-threatening)
    CRITICAL_EVENT_TYPES = {
        WeatherEventType.TORNADO,
        WeatherEventType.FLASH_FLOOD,
        WeatherEventType.EARTHQUAKE,
        WeatherEventType.TSUNAMI,
        WeatherEventType.VOLCANIC_ACTIVITY,
        WeatherEventType.HURRICANE,
        WeatherEventType.EVACUATION,
        WeatherEventType.CIVIL_DANGER,
        WeatherEventType.AMBER_ALERT,
        WeatherEventType.HAZARDOUS_MATERIALS,
        WeatherEventType.RADIOLOGICAL_HAZARD,
    }
    
    # Weather event types that create alarms based on severity
    SEVERITY_DEPENDENT_EVENT_TYPES = {
        WeatherEventType.SEVERE_THUNDERSTORM,
        WeatherEventType.EXTREME_WIND,
        WeatherEventType.FLOOD,
        WeatherEventType.COASTAL_FLOOD,
        WeatherEventType.BLIZZARD,
        WeatherEventType.WINTER_STORM,
        WeatherEventType.ICE_STORM,
        WeatherEventType.TROPICAL_STORM,
        WeatherEventType.STORM_SURGE,
        WeatherEventType.EXTREME_HEAT,
        WeatherEventType.EXTREME_COLD,
        WeatherEventType.WIND_CHILL,
        WeatherEventType.ASHFALL,
        WeatherEventType.AVALANCHE,
        WeatherEventType.WILDFIRE,
        WeatherEventType.RED_FLAG_CONDITIONS,
        WeatherEventType.DUST_STORM,
        WeatherEventType.HIGH_SURF,
        WeatherEventType.GALE,
        WeatherEventType.BLUE_ALERT,
        WeatherEventType.LAW_ENFORCEMENT,
    }
    
    # Weather event types that are informational and don't create alarms
    INFORMATIONAL_EVENT_TYPES = {
        WeatherEventType.TEST_MESSAGE,
        WeatherEventType.ADMINISTRATIVE,
        WeatherEventType.SPECIAL_WEATHER,
        WeatherEventType.AIR_QUALITY,
        WeatherEventType.SMOKE,
        WeatherEventType.MARINE_WEATHER,  # Most marine weather is for boaters
        WeatherEventType.AURORA,  # Beautiful but not dangerous
        WeatherEventType.METEOR_SHOWER,  # Interesting but not alarming
        WeatherEventType.POWER_OUTAGE,  # Usually handled by other systems
        WeatherEventType.TELEPHONE_OUTAGE,  # Infrastructure, not weather
    }
    
    # Event type to base alarm level mapping (before severity adjustment)
    EVENT_TYPE_TO_BASE_ALARM_LEVEL = {
        # Always CRITICAL - immediate life threat
        WeatherEventType.TORNADO: AlarmLevel.CRITICAL,
        WeatherEventType.FLASH_FLOOD: AlarmLevel.CRITICAL,
        WeatherEventType.EARTHQUAKE: AlarmLevel.CRITICAL,
        WeatherEventType.TSUNAMI: AlarmLevel.CRITICAL,
        WeatherEventType.VOLCANIC_ACTIVITY: AlarmLevel.CRITICAL,
        WeatherEventType.EVACUATION: AlarmLevel.CRITICAL,
        WeatherEventType.CIVIL_DANGER: AlarmLevel.CRITICAL,
        WeatherEventType.AMBER_ALERT: AlarmLevel.CRITICAL,
        WeatherEventType.HAZARDOUS_MATERIALS: AlarmLevel.CRITICAL,
        WeatherEventType.RADIOLOGICAL_HAZARD: AlarmLevel.CRITICAL,
        
        # Usually WARNING - significant threat but some time to respond
        WeatherEventType.HURRICANE: AlarmLevel.WARNING,
        WeatherEventType.SEVERE_THUNDERSTORM: AlarmLevel.WARNING,
        WeatherEventType.EXTREME_WIND: AlarmLevel.WARNING,
        WeatherEventType.FLOOD: AlarmLevel.WARNING,
        WeatherEventType.COASTAL_FLOOD: AlarmLevel.WARNING,
        WeatherEventType.BLIZZARD: AlarmLevel.WARNING,
        WeatherEventType.WINTER_STORM: AlarmLevel.WARNING,
        WeatherEventType.ICE_STORM: AlarmLevel.WARNING,
        WeatherEventType.TROPICAL_STORM: AlarmLevel.WARNING,
        WeatherEventType.STORM_SURGE: AlarmLevel.WARNING,
        WeatherEventType.WILDFIRE: AlarmLevel.WARNING,
        WeatherEventType.ASHFALL: AlarmLevel.WARNING,
        WeatherEventType.AVALANCHE: AlarmLevel.WARNING,
        
        # Usually INFO - notable conditions requiring attention
        WeatherEventType.EXTREME_HEAT: AlarmLevel.INFO,
        WeatherEventType.EXTREME_COLD: AlarmLevel.INFO,
        WeatherEventType.WIND_CHILL: AlarmLevel.INFO,
        WeatherEventType.RED_FLAG_CONDITIONS: AlarmLevel.INFO,
        WeatherEventType.DUST_STORM: AlarmLevel.INFO,
        WeatherEventType.HIGH_SURF: AlarmLevel.INFO,
        WeatherEventType.GALE: AlarmLevel.INFO,
        WeatherEventType.BLUE_ALERT: AlarmLevel.INFO,
        WeatherEventType.LAW_ENFORCEMENT: AlarmLevel.INFO,
    }
    
    # Alarm lifetime mapping based on event type (in seconds)
    EVENT_TYPE_TO_LIFETIME = {
        # Immediate action events - shorter lifetimes
        WeatherEventType.TORNADO: 30 * 60,           # 30 minutes
        WeatherEventType.FLASH_FLOOD: 60 * 60,       # 1 hour
        WeatherEventType.EARTHQUAKE: 15 * 60,        # 15 minutes
        WeatherEventType.TSUNAMI: 60 * 60,           # 1 hour
        WeatherEventType.EVACUATION: 30 * 60,        # 30 minutes
        
        # Severe weather events - medium lifetimes
        WeatherEventType.SEVERE_THUNDERSTORM: 2 * 60 * 60,    # 2 hours
        WeatherEventType.EXTREME_WIND: 4 * 60 * 60,           # 4 hours
        WeatherEventType.HURRICANE: 24 * 60 * 60,             # 24 hours
        WeatherEventType.TROPICAL_STORM: 12 * 60 * 60,        # 12 hours
        WeatherEventType.WILDFIRE: 8 * 60 * 60,               # 8 hours
        
        # Long-duration events
        WeatherEventType.BLIZZARD: 12 * 60 * 60,              # 12 hours
        WeatherEventType.WINTER_STORM: 8 * 60 * 60,           # 8 hours
        WeatherEventType.ICE_STORM: 6 * 60 * 60,              # 6 hours
        WeatherEventType.FLOOD: 6 * 60 * 60,                  # 6 hours
        WeatherEventType.COASTAL_FLOOD: 4 * 60 * 60,          # 4 hours
        
        # Temperature/environmental events
        WeatherEventType.EXTREME_HEAT: 12 * 60 * 60,          # 12 hours
        WeatherEventType.EXTREME_COLD: 12 * 60 * 60,          # 12 hours
        WeatherEventType.WIND_CHILL: 8 * 60 * 60,             # 8 hours
        WeatherEventType.RED_FLAG_CONDITIONS: 6 * 60 * 60,    # 6 hours
        WeatherEventType.DUST_STORM: 3 * 60 * 60,             # 3 hours
        
        # Public safety events
        WeatherEventType.AMBER_ALERT: 12 * 60 * 60,           # 12 hours
        WeatherEventType.BLUE_ALERT: 4 * 60 * 60,             # 4 hours
        WeatherEventType.CIVIL_DANGER: 4 * 60 * 60,           # 4 hours
        WeatherEventType.HAZARDOUS_MATERIALS: 6 * 60 * 60,    # 6 hours
        WeatherEventType.RADIOLOGICAL_HAZARD: 8 * 60 * 60,    # 8 hours
        
        # Marine/geological events
        WeatherEventType.HIGH_SURF: 4 * 60 * 60,              # 4 hours
        WeatherEventType.GALE: 6 * 60 * 60,                   # 6 hours
        WeatherEventType.VOLCANIC_ACTIVITY: 24 * 60 * 60,     # 24 hours
        WeatherEventType.ASHFALL: 8 * 60 * 60,                # 8 hours
        WeatherEventType.AVALANCHE: 2 * 60 * 60,              # 2 hours
        WeatherEventType.STORM_SURGE: 4 * 60 * 60,            # 4 hours
    }
    
    # Default lifetime for events not specified above
    DEFAULT_LIFETIME_SECS = 4 * 60 * 60  # 4 hours
    
    def should_create_alarm(self, weather_alert: WeatherAlert) -> bool:
        if weather_alert.status in [AlertStatus.TEST, AlertStatus.EXERCISE, AlertStatus.DRAFT]:
            return False

        if weather_alert.event_type in self.CRITICAL_EVENT_TYPES:
            return True

        if weather_alert.event_type in self.SEVERITY_DEPENDENT_EVENT_TYPES:
            if weather_alert.severity in [AlertSeverity.EXTREME, AlertSeverity.SEVERE]:
                return True
            if ( weather_alert.severity == AlertSeverity.MODERATE
                 and weather_alert.urgency == AlertUrgency.IMMEDIATE ):
                return True

        if weather_alert.event_type in self.INFORMATIONAL_EVENT_TYPES:
            return False

        # Conservative fallback for unclassified event types: alarm only on EXTREME.
        if weather_alert.severity == AlertSeverity.EXTREME:
            return True

        return False
    
    def get_alarm_level(self, weather_alert: WeatherAlert) -> Optional[AlarmLevel]:
        if not self.should_create_alarm(weather_alert):
            return None

        base_level = self.EVENT_TYPE_TO_BASE_ALARM_LEVEL.get(
            weather_alert.event_type,
            AlarmLevel.INFO
        )

        # Severity adjustment: EXTREME always CRITICAL; SEVERE at least WARNING (CRITICAL
        # only if base is CRITICAL); MODERATE caps at WARNING; MINOR caps at INFO.
        if weather_alert.severity == AlertSeverity.EXTREME:
            return AlarmLevel.CRITICAL
        elif weather_alert.severity == AlertSeverity.SEVERE:
            if base_level == AlarmLevel.CRITICAL:
                return AlarmLevel.CRITICAL
            else:
                return AlarmLevel.WARNING
        elif weather_alert.severity == AlertSeverity.MODERATE:
            if base_level == AlarmLevel.CRITICAL:
                return AlarmLevel.WARNING
            elif base_level == AlarmLevel.WARNING:
                return AlarmLevel.WARNING
            else:
                return AlarmLevel.INFO
        else:  # MINOR
            return AlarmLevel.INFO
    
    def get_alarm_lifetime(self, weather_alert: WeatherAlert) -> int:
        """ Alarm lifetime in seconds. """
        if weather_alert.expires:
            now = datetimeproxy.now()
            if weather_alert.expires > now:
                lifetime_seconds = int((weather_alert.expires - now).total_seconds())
                # Cap at reasonable maximum (48 hours) and minimum (15 minutes)
                return max(15 * 60, min(lifetime_seconds, 48 * 60 * 60))

        return self.EVENT_TYPE_TO_LIFETIME.get(
            weather_alert.event_type,
            self.DEFAULT_LIFETIME_SECS
        )
    
    def get_alarm_type(self, weather_alert: WeatherAlert) -> str:
        """ Alarm-type string; canonical event-type name groups equivalent alerts
        across different weather sources in the alarm signature. """
        return weather_alert.event_type.name
    
    def create_sensor_responses(self, weather_alert: WeatherAlert) -> List[SensorResponse]:
        detail_attrs = {
            'Event Type': weather_alert.event_type.label,
            'Source Event': weather_alert.event,
            'Severity': weather_alert.severity.label,
            'Urgency': weather_alert.urgency.label,
            'Certainty': weather_alert.certainty.label,
            'Category': weather_alert.category.label,
            'Headline': weather_alert.headline,
            'Affected Areas': weather_alert.affected_areas,
            'Effective': weather_alert.effective.strftime('%Y-%m-%d %H:%M:%S') if weather_alert.effective else 'Unknown',
        }
        
        if weather_alert.expires:
            detail_attrs['Expires'] = weather_alert.expires.strftime('%Y-%m-%d %H:%M:%S')

        if weather_alert.instruction:
            instruction = weather_alert.instruction
            if len(instruction) > 200:
                instruction = instruction[:200] + '...'
            detail_attrs['Instructions'] = instruction

        if weather_alert.description:
            description = weather_alert.description
            if len(description) > 300:
                description = description[:300] + '...'
            detail_attrs['Description'] = description

        # Weather alerts have no associated sensor; build a synthetic integration key
        # from event type and timestamp.
        alert_id = f'{weather_alert.event_type.name}.{weather_alert.effective.timestamp() if weather_alert.effective else "unknown"}'
        integration_key = IntegrationKey(
            integration_id='weather',
            integration_name=f'alert.{alert_id}'
        )

        return [SensorResponse(
            integration_key=integration_key,
            value='active',
            timestamp=weather_alert.effective or datetimeproxy.now(),
            sensor=None,
            detail_attrs=detail_attrs,
            has_event_video_clip=False,
        )]
    
    def create_alarm(self, weather_alert: WeatherAlert) -> Optional[Alarm]:
        if not self.should_create_alarm(weather_alert):
            logger.debug(f'Weather alert does not warrant system alarm: {weather_alert.event_type.label}')
            return None

        alarm_level = self.get_alarm_level(weather_alert)
        if not alarm_level:
            logger.debug(f'Weather alert does not map to alarm level: {weather_alert.event_type.label}')
            return None

        title = weather_alert.headline
        if not title or len(title.strip()) == 0:
            title = f"{weather_alert.event_type.label} - {weather_alert.severity.label}"

        # source_alarm_id ties this Alarm record back to the specific upstream alert,
        # so repeated polls of the same active alert refresh expiry without incrementing
        # alarm_count.
        alarm = Alarm(
            alarm_source=AlarmSource.WEATHER,
            alarm_type=self.get_alarm_type(weather_alert),
            alarm_level=alarm_level,
            title=title,
            sensor_response_list=self.create_sensor_responses(weather_alert),
            security_level=SecurityLevel.OFF,  # Weather alarms apply to all security levels
            alarm_lifetime_secs=self.get_alarm_lifetime(weather_alert),
            timestamp=datetimeproxy.now(),
            source_alarm_id=weather_alert.alert_id,
        )
        
        logger.info(f'Created weather alarm: {alarm.signature} - {alarm.title}')
        return alarm
    
    def create_alarms_from_weather_alerts(self, weather_alerts: List[WeatherAlert]) -> List[Alarm]:
        alarms = []
        
        for weather_alert in weather_alerts:
            try:
                alarm = self.create_alarm(weather_alert)
                if alarm:
                    alarms.append(alarm)
            except Exception as e:
                logger.exception(f'Error creating alarm from weather alert {weather_alert.event_type.label}: {e}')
                continue
        
        logger.info(f'Created {len(alarms)} system alarms from {len(weather_alerts)} weather alerts')
        return alarms
