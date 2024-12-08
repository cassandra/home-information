from datetime import datetime, timedelta
import random
from typing import List

from hi.apps.alert.alarm import Alarm
from hi.apps.alert.alert import Alert
from hi.apps.alert.alert_status import AlertStatusData
from hi.apps.alert.enums import AlarmLevel, AlarmSource, SecurityPosture
import hi.apps.common.datetimeproxy as datetimeproxy


class AlertSyntheticData:

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
            security_posture = random_impl.choice( list( SecurityPosture ))
            alarm_idx = 0
            alarm_title = f'Alarm-{alert_idx}-{alarm_idx}'
            alarm_timestamp = reference_datetime - timedelta( seconds = alarm_time_offsets[alarm_idx] )
            first_alarm = Alarm(
                alarm_source = alarm_source,
                alarm_type = alarm_type,
                alarm_level= alarm_level,
                title = alarm_title,
                details = f'Details for {alarm_title}. Seed = {seed} ',
                security_posture = security_posture,
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
                    details = f'Details for {alarm_title}. Seed = {seed} ',
                    security_posture = security_posture,
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
    
