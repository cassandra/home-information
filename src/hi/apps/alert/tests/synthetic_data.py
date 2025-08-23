from datetime import datetime, timedelta
import random
from typing import List

from hi.apps.alert.alarm import Alarm
from hi.apps.alert.alert import Alert
from hi.apps.alert.alert_status import AlertStatusData
from hi.apps.alert.enums import AlarmLevel, AlarmSource
import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.security.enums import SecurityLevel


class AlertSyntheticData:

    @classmethod
    def create_single_alarm_alert( cls,
                                   alarm_level         : AlarmLevel = AlarmLevel.INFO,
                                   alarm_source        : AlarmSource = AlarmSource.EVENT,
                                   alarm_type          : str = 'Motion Detection',
                                   title               : str = None,
                                   has_image           : bool = False,
                                   detail_attrs        : dict = None,
                                   security_level      : SecurityLevel = SecurityLevel.LOW,
                                   alarm_lifetime_secs : int = 300,
                                   timestamp           : datetime = None ) -> Alert:
        """Create a single alert with one alarm for testing."""
        
        if not timestamp:
            timestamp = datetimeproxy.now()
        if not title:
            title = f'{alarm_level.label}: {alarm_type}'
        if not detail_attrs:
            detail_attrs = {'Location': 'Kitchen', 'Sensor': 'Motion-01'}

        image_url = '/static/img/hi-icon-196x196.png' if has_image else None
        
        alarm = Alarm(
            alarm_source = alarm_source,
            alarm_type = alarm_type,
            alarm_level = alarm_level,
            title = title,
            source_details_list = [
                AlarmSourceDetails(
                    detail_attrs = detail_attrs,
                    image_url = image_url,
                ),
            ],
            security_level = security_level,
            alarm_lifetime_secs = alarm_lifetime_secs,
            timestamp = timestamp,
        )
        
        return Alert( first_alarm = alarm )

    @classmethod
    def create_multiple_alarm_alert( cls,
                                     alarm_count         : int = 3,
                                     alarm_level         : AlarmLevel = AlarmLevel.WARNING,
                                     alarm_source        : AlarmSource = AlarmSource.EVENT,
                                     alarm_type          : str = 'Repeated Motion',
                                     base_title          : str = 'Repeated motion detected',
                                     has_image           : bool = True,
                                     base_detail_attrs   : dict = None,
                                     security_level      : SecurityLevel = SecurityLevel.LOW,
                                     alarm_lifetime_secs : int = 600,
                                     reference_datetime  : datetime = None,
                                     time_interval_mins  : int = 1 ) -> Alert:
        """Create a single alert with multiple alarms for testing."""
        
        if not reference_datetime:
            reference_datetime = datetimeproxy.now()
        if not base_detail_attrs:
            base_detail_attrs = {'Location': 'Living Room', 'Sensor': 'Motion-02'}

        # Create first alarm
        image_url = '/static/img/hi-icon-196x196.png' if has_image else None
        detail_attrs = dict(base_detail_attrs)
        detail_attrs.update({'Count': f'1 of {alarm_count}'})
        
        first_alarm = Alarm(
            alarm_source = alarm_source,
            alarm_type = alarm_type,
            alarm_level = alarm_level,
            title = f'{alarm_level.label}: {base_title}',
            source_details_list = [
                AlarmSourceDetails(
                    detail_attrs = detail_attrs,
                    image_url = image_url,
                ),
            ],
            security_level = security_level,
            alarm_lifetime_secs = alarm_lifetime_secs,
            timestamp = reference_datetime - timedelta(minutes=time_interval_mins * (alarm_count - 1)),
        )
        
        alert = Alert( first_alarm = first_alarm )
        
        # Add additional alarms
        for i in range(2, alarm_count + 1):
            detail_attrs = dict(base_detail_attrs)
            detail_attrs.update({'Count': f'{i} of {alarm_count}'})
            
            additional_alarm = Alarm(
                alarm_source = alarm_source,
                alarm_type = alarm_type,
                alarm_level = alarm_level,
                title = f'{alarm_level.label}: {base_title} ({i})',
                source_details_list = [
                    AlarmSourceDetails(
                        detail_attrs = detail_attrs,
                        image_url = image_url if i == 2 else None,  # Only second alarm has image
                    ),
                ],
                security_level = security_level,
                alarm_lifetime_secs = alarm_lifetime_secs,
                timestamp = reference_datetime - timedelta(minutes=time_interval_mins * (alarm_count - i)),
            )
            alert.add_alarm( additional_alarm )
        
        return alert

    @classmethod
    def create_event_based_alert( cls,
                                  event_name     : str = 'Door Open Event',
                                  entity_name    : str = 'front-door-sensor',
                                  location       : str = 'Front Door',
                                  previous_state : str = 'Closed',
                                  current_state  : str = 'Open',
                                  has_image      : bool = False,
                                  alarm_level    : AlarmLevel = AlarmLevel.INFO ) -> Alert:
        """Create an event-based alert for testing."""
        
        image_url = '/static/img/hi-icon-196x196.png' if has_image else None
        detail_attrs = {
            'Event': event_name,
            'Location': location,
            'Previous State': previous_state,
            'Current State': current_state,
            'Entity': entity_name
        }
        
        alarm = Alarm(
            alarm_source = AlarmSource.EVENT,
            alarm_type = event_name,
            alarm_level = alarm_level,
            title = f'{alarm_level.label}: {location} {event_name.lower()}',
            source_details_list = [
                AlarmSourceDetails(
                    detail_attrs = detail_attrs,
                    image_url = image_url,
                ),
            ],
            security_level = SecurityLevel.LOW,
            alarm_lifetime_secs = 180,
            timestamp = datetimeproxy.now(),
        )
        
        return Alert( first_alarm = alarm )

    @classmethod
    def create_weather_alert( cls,
                              alert_type       : str = 'Tornado Warning',
                              location         : str = 'Travis County, TX',
                              urgency          : str = 'Immediate',
                              severity         : str = 'Extreme',
                              expires_in_mins  : int = 45,
                              has_image        : bool = False ) -> Alert:
        """Create a weather-based alert for testing."""
        
        image_url = '/static/img/hi-icon-196x196.png' if has_image else None
        detail_attrs = {
            'Alert Type': alert_type,
            'Location': location,
            'Urgency': urgency,
            'Severity': severity,
            'Event': alert_type.split()[0],  # 'Tornado' from 'Tornado Warning'
            'Effective': 'Now',
            'Expires': f'In {expires_in_mins} minutes'
        }
        
        alarm = Alarm(
            alarm_source = AlarmSource.WEATHER,
            alarm_type = 'Severe Weather',
            alarm_level = AlarmLevel.CRITICAL,
            title = f'CRITICAL: {alert_type} issued',
            source_details_list = [
                AlarmSourceDetails(
                    detail_attrs = detail_attrs,
                    image_url = image_url,
                ),
            ],
            security_level = SecurityLevel.HIGH,
            alarm_lifetime_secs = expires_in_mins * 60,
            timestamp = datetimeproxy.now(),
        )
        
        return Alert( first_alarm = alarm )

    @classmethod
    def create_random_alert_status_data( cls,
                                         reference_datetime  : datetime  = None,
                                         seed                : int       = None ) -> AlertStatusData:
        alert_list = cls.create_random_alert_list(
            reference_datetime = reference_datetime,
            seed = seed,
        )
        max_priority_alert = alert_list[0]
        max_recent_alarm = alert_list[0].alarm_list[0]
        for alert in alert_list:
            if alert.alert_priority > max_priority_alert.alert_priority:
                max_priority_alert = alert
            for alarm in alert.alarm_list:
                if alarm.timestamp > max_recent_alarm.timestamp:
                    max_recent_alarm = alarm
                continue
            continue
        
        return AlertStatusData(
            alert_list = alert_list,
            max_audio_signal = max_priority_alert.audio_signal,
            new_audio_signal = max_recent_alarm.audio_signal,
        )

    @classmethod
    def create_random_alert_list( cls,
                                  reference_datetime   : datetime  = None,
                                  alarm_lifetime_secs  : int       = None,
                                  seed                 : int       = None ) -> List[ Alert ]:
        random_impl = random.Random( seed ) if seed else random

        if not reference_datetime:
            reference_datetime = datetimeproxy.now()
        if not alarm_lifetime_secs:
            alarm_lifetime_secs = random_impl.randint( 300, 600 )

        num_alerts = random_impl.randint( 1, 4 )
        alert_list = list()
        for alert_idx in range( num_alerts ):
            alarm_count = random_impl.randint( 1, 4 )
            alarm_time_offsets = cls.generate_time_offsets( length = num_alerts,
                                                            max_seconds = 120,
                                                            random_impl = random_impl )
            alarm_source = random_impl.choice( list( AlarmSource ))
            alarm_type = f'Alarm Type {num_alerts}'
            alarm_level = random_impl.choice([ AlarmLevel.INFO,
                                               AlarmLevel.WARNING,
                                               AlarmLevel.CRITICAL ])
            security_level = random_impl.choice( list( SecurityLevel ))
            alarm_idx = 0
            alarm_title = f'Alarm-{alert_idx}-{alarm_idx}'
            alarm_timestamp = reference_datetime - timedelta( seconds = alarm_time_offsets[alarm_idx] )
            first_alarm = Alarm(
                alarm_source = alarm_source,
                alarm_type = alarm_type,
                alarm_level= alarm_level,
                title = alarm_title,
                source_details_list = [
                    AlarmSourceDetails(
                        detail_attrs = { 'Notes': f'Details for {alarm_title}. Seed = {seed} ' },
                        image_url = '/static/img/hi-icon-196x196.png',
                    ),
                ],
                security_level = security_level,
                alarm_lifetime_secs = alarm_lifetime_secs,
                timestamp = alarm_timestamp,
            )
            alert = Alert(
                first_alarm = first_alarm,
            )
            for extra_idx in range( alarm_count - 1 ):
                alarm_idx = extra_idx + 1
                alarm_title = f'Alarm-{alert_idx}-{alarm_idx}'
                alarm_timestamp = reference_datetime - timedelta( seconds = alarm_time_offsets[alarm_idx] )
                alarm = Alarm(
                    alarm_source = alarm_source,
                    alarm_type = alarm_type,
                    alarm_level= alarm_level,
                    title = alarm_title,
                    source_details_list = [
                        AlarmSourceDetails(
                            detail_attrs = { 'Notes': f'Details for {alarm_title}. Seed = {seed} ' },
                            image_url = '/static/img/hi-icon-196x196.png',
                        ),
                    ],
                    security_level = security_level,
                    alarm_lifetime_secs = alarm_lifetime_secs,
                    timestamp = alarm_timestamp,
                )
                alert.add_alarm( alarm )
                continue
            alert_list.append( alert )
            continue

        return alert_list

    @classmethod
    def generate_time_offsets( cls,
                               length       : int,
                               max_seconds  : int,
                               random_impl  : random.Random ) -> List[ int ]:
        random_impl = random_impl or random
        return sorted( random_impl.randint( 0, max_seconds ) for _ in range(length) )
    
