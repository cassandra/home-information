"""
Weather Alert to System Alarm Mapping

This module handles the conversion of weather alerts (using canonical WeatherEventType)
into system alarms that can trigger notifications and user alerts.

The mapping strategy is based on:
1. Event type significance (life-threatening vs informational)
2. Alert severity level 
3. Alert status (actual vs test/exercise)
4. Alert urgency and certainty
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
        """
        Determine if a weather alert should create a system alarm.
        
        Args:
            weather_alert: The weather alert to evaluate
            
        Returns:
            True if this alert should create a system alarm
        """
        # Never create alarms for test messages or exercises
        if weather_alert.status in [AlertStatus.TEST, AlertStatus.EXERCISE, AlertStatus.DRAFT]:
            return False
        
        # Always create alarms for critical event types
        if weather_alert.event_type in self.CRITICAL_EVENT_TYPES:
            return True
        
        # For severity-dependent events, check severity level
        if weather_alert.event_type in self.SEVERITY_DEPENDENT_EVENT_TYPES:
            # Create alarms for EXTREME and SEVERE, optionally for MODERATE based on urgency
            if weather_alert.severity in [AlertSeverity.EXTREME, AlertSeverity.SEVERE]:
                return True
            if ( weather_alert.severity == AlertSeverity.MODERATE
                 and weather_alert.urgency == AlertUrgency.IMMEDIATE ):
                return True
        
        # Don't create alarms for informational events
        if weather_alert.event_type in self.INFORMATIONAL_EVENT_TYPES:
            return False
        
        # For other event types, be conservative - only create for EXTREME severity
        if weather_alert.severity == AlertSeverity.EXTREME:
            return True
        
        return False
    
    def get_alarm_level(self, weather_alert: WeatherAlert) -> Optional[AlarmLevel]:
        """
        Determine the appropriate alarm level for a weather alert.
        
        Args:
            weather_alert: The weather alert to map
            
        Returns:
            The appropriate AlarmLevel or None if no alarm should be created
        """
        if not self.should_create_alarm(weather_alert):
            return None
        
        # Get base alarm level from event type
        base_level = self.EVENT_TYPE_TO_BASE_ALARM_LEVEL.get(
            weather_alert.event_type, 
            AlarmLevel.INFO
        )
        
        # Adjust based on severity
        if weather_alert.severity == AlertSeverity.EXTREME:
            # Extreme severity always gets CRITICAL
            return AlarmLevel.CRITICAL
        elif weather_alert.severity == AlertSeverity.SEVERE:
            # Severe gets at least WARNING, could be CRITICAL for critical event types
            if base_level == AlarmLevel.CRITICAL:
                return AlarmLevel.CRITICAL
            else:
                return AlarmLevel.WARNING
        elif weather_alert.severity == AlertSeverity.MODERATE:
            # Moderate gets at most WARNING
            if base_level == AlarmLevel.CRITICAL:
                return AlarmLevel.WARNING
            elif base_level == AlarmLevel.WARNING:
                return AlarmLevel.WARNING
            else:
                return AlarmLevel.INFO
        else:  # MINOR
            # Minor severity gets at most INFO
            return AlarmLevel.INFO
    
    def get_alarm_lifetime(self, weather_alert: WeatherAlert) -> int:
        """
        Calculate appropriate alarm lifetime for the weather alert.
        
        Args:
            weather_alert: The weather alert to calculate lifetime for
            
        Returns:
            Alarm lifetime in seconds
        """
        # If the weather alert has an expiration time, use that
        if weather_alert.expires:
            now = datetimeproxy.now()
            if weather_alert.expires > now:
                lifetime_seconds = int((weather_alert.expires - now).total_seconds())
                # Cap at reasonable maximum (48 hours) and minimum (15 minutes)
                return max(15 * 60, min(lifetime_seconds, 48 * 60 * 60))
        
        # Use event type-based lifetime
        return self.EVENT_TYPE_TO_LIFETIME.get(
            weather_alert.event_type, 
            self.DEFAULT_LIFETIME_SECS
        )
    
    def get_alarm_type(self, weather_alert: WeatherAlert) -> str:
        """
        Generate alarm type string for the weather alert.
        
        This creates a consistent alarm type based on the canonical event type,
        which will be used in the alarm signature for grouping similar alerts.
        
        Args:
            weather_alert: The weather alert to generate type for
            
        Returns:
            A string representing the alarm type
        """
        # Use the canonical event type name as the alarm type
        # This ensures consistent grouping across different weather sources
        return weather_alert.event_type.name
    
    def create_sensor_responses(self, weather_alert: WeatherAlert) -> List[SensorResponse]:
        """
        Create sensor responses from weather alert information.
        
        Args:
            weather_alert: The weather alert to create sensor responses for
            
        Returns:
            List of SensorResponse for this weather alert
        """
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
        
        # Add optional fields if available
        if weather_alert.expires:
            detail_attrs['Expires'] = weather_alert.expires.strftime('%Y-%m-%d %H:%M:%S')
        
        if weather_alert.instruction:
            # Truncate instructions for alarm details
            instruction = weather_alert.instruction
            if len(instruction) > 200:
                instruction = instruction[:200] + '...'
            detail_attrs['Instructions'] = instruction
        
        # Add brief description
        if weather_alert.description:
            description = weather_alert.description
            if len(description) > 300:
                description = description[:300] + '...'
            detail_attrs['Description'] = description
        
        # Create a SensorResponse for weather alerts
        # Weather alerts don't have sensors, so we use a synthetic integration key
        # Use event type and timestamp to create a unique identifier
        alert_id = f'{weather_alert.event_type.name}.{weather_alert.effective.timestamp() if weather_alert.effective else "unknown"}'
        integration_key = IntegrationKey(
            integration_id='weather',
            integration_name=f'alert.{alert_id}'
        )
        
        return [SensorResponse(
            integration_key=integration_key,
            value='active',  # Weather alerts are active when they exist
            timestamp=weather_alert.effective or datetimeproxy.now(),
            sensor=None,  # No sensor for weather alerts
            detail_attrs=detail_attrs,
            source_image_url=None,  # Weather alerts don't have images
            has_video_stream=False
        )]
    
    def create_alarm(self, weather_alert: WeatherAlert) -> Optional[Alarm]:
        """
        Create a system alarm from a weather alert.
        
        Args:
            weather_alert: The weather alert to convert
            
        Returns:
            An Alarm object or None if no alarm should be created
        """
        # Check if this alert should create an alarm
        if not self.should_create_alarm(weather_alert):
            logger.debug(f'Weather alert does not warrant system alarm: {weather_alert.event_type.label}')
            return None
        
        # Get alarm level
        alarm_level = self.get_alarm_level(weather_alert)
        if not alarm_level:
            logger.debug(f'Weather alert does not map to alarm level: {weather_alert.event_type.label}')
            return None
        
        # Create alarm title from headline or event type
        title = weather_alert.headline
        if not title or len(title.strip()) == 0:
            title = f"{weather_alert.event_type.label} - {weather_alert.severity.label}"
        
        # Create the alarm
        alarm = Alarm(
            alarm_source=AlarmSource.WEATHER,
            alarm_type=self.get_alarm_type(weather_alert),
            alarm_level=alarm_level,
            title=title,
            sensor_response_list=self.create_sensor_responses(weather_alert),
            security_level=SecurityLevel.OFF,  # Weather alarms apply to all security levels
            alarm_lifetime_secs=self.get_alarm_lifetime(weather_alert),
            timestamp=datetimeproxy.now(),
        )
        
        logger.info(f'Created weather alarm: {alarm.signature} - {alarm.title}')
        return alarm
    
    def create_alarms_from_weather_alerts(self, weather_alerts: List[WeatherAlert]) -> List[Alarm]:
        """
        Process a list of weather alerts and create system alarms for qualifying ones.
        
        Args:
            weather_alerts: List of weather alerts to process
            
        Returns:
            List of created Alarm objects
        """
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
