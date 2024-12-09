from datetime import datetime
import logging
import threading

import hi.apps.common.datetimeproxy as datetimeproxy

from .alarm import Alarm
from .alert import Alert
from .enums import AlarmLevel

logger = logging.getLogger(__name__)


class AlertQueue:

    MAX_ALERT_LIST_SIZE = 50
    
    def __init__(self):
        self._alert_list = list()


        



        from hi.apps.alert.tests.synthetic_data import AlertSyntheticData
        self._alert_list = AlertSyntheticData.create_random_alert_list(
            reference_datetime = datetimeproxy.iso_naive_to_datetime_utc('2024-12-08T18:01:54'),
            alarm_lifetime_secs = 999999,
            # seed = 23456789,  # Alerts = 1, Alarms = 1W
            # seed = 23456780,  # Alerts = 4, Alarms = 4C, 1C, 2C, 3W
            seed = 23456781,  # Alerts = 2, Alarms = 1I, 2C
        )
        print( f'\n\nSET SYNTHETIC ALERT LIST: size={len(self._alert_list)}\n' )




        

        
        self._active_alerts_lock = threading.Lock()
        self._last_changed_datetime = datetimeproxy.now()
        return

    def __bool__(self):
        return bool( self._alert_list )
    
    def __len__(self):
        return len( self._alert_list )

    @property
    def unacknowledged_alert_list(self):
        return [ x for x in self._alert_list if not x.is_acknowledged ]
    
    def get_alert( self, alert_id : str ) -> Alert:
        for alert in self._alert_list:
            if alert.id == alert_id:
                return alert
            continue
        raise KeyError( f'Alert not found for {alert_id}' )
        
    def get_most_important_alert( self, since_datetime : datetime = None ):
        """
        Returns the active alert that has the highest priority and which was
        created since the "since_datetime" passed (if any).  If there are
        multiple events of the same priority, then an arbitrary one is
        returned. Returns None if there are no active alerts in the
        specified time frame.
        """
        try:
            self._active_alerts_lock.acquire()
            
            if len(self._alert_list) < 1:
                return None
            
            if since_datetime is None:
                since_datetime = datetimeproxy.min()
                
            max_alert = None
            for alert in self._alert_list:
                if alert.is_acknowledged:
                    continue
                if alert.start_datetime <= since_datetime:
                    continue
                if max_alert is None:
                    max_alert = alert
                elif alert.alert_priority > max_alert.alert_priority:
                    max_alert = alert
                continue
        finally:
            self._active_alerts_lock.release()
        return

    def get_most_recent_alarm( self, since_datetime : datetime = None ):
        """
        Of all the alarms in all the alerts, return the most recent
        one that is new than "since_datetime".  Original use of this routine
        was to find a URL to switch to when automatically changing displays
        based on alarms.
        """
        try:
            self._active_alerts_lock.acquire()
            
            if len(self._alert_list) < 1:
                return None
            
            if since_datetime is None:
                since_datetime = datetimeproxy.min()

            latest_alarm = None
            latest_alarm_datetime = datetimeproxy.min()
            for alert in self._alert_list:
                if alert.is_acknowledged:
                    continue
                alarm = alert.get_latest_alarm()
                if not alarm:
                    continue
                if alarm.timestamp <= since_datetime:
                    continue
                if alarm.timestamp >= latest_alarm_datetime:
                    latest_alarm = alarm
                    latest_alarm_datetime = alarm.timestamp
                continue
            
            return latest_alarm

        finally:
            self._active_alerts_lock.release()
        return
    
    def add_alarm( self, alarm : Alarm ):
        if alarm.alarm_level == AlarmLevel.NONE:
            raise ValueError( f'Alarm not alert-worthy: {alarm}'  )
        try:
            self._active_alerts_lock.acquire()
            for alert in self._alert_list:
                if not alert.is_matching_alarm( alarm = alarm ):
                    continue
                alert._add_alarm( alarm = alarm )
                self._last_changed_datetime = datetimeproxy.now()
                logger.debug( f'Added to existing alert: alarm={alarm}, alert={alert}' )
                return
            
            new_alert = Alert( first_alarm = alarm )
            self._alert_list.append( new_alert )
            self._last_changed_datetime = datetimeproxy.now()
            logger.debug( f'Added new alert: {new_alert}' )
            return
    
        finally:
            self._active_alerts_lock.release()
        return

    def acknowledge_alert( self, alert_id : str ):
        try:
            self._active_alerts_lock.acquire()

            for alert in self._alert_list:
                if alert.id != alert_id:
                    continue
                alert.is_acknowledged = True
                self._last_changed_datetime = datetimeproxy.now()
                return True

            raise KeyError( f'Alert not found for {alert_id}' )
        finally:
            self._active_alerts_lock.release()

    def remove_expired_or_acknowledged_alerts(self):
        try:
            self._active_alerts_lock.acquire()

            logger.debug( f'Alert Check: List size = {len(self._alert_list)}')
            if len( self._alert_list ) < 1:
                return
        
            now_datetime = datetimeproxy.now()
            new_list = list()
            for alert in self._alert_list:
                if alert.end_datetime <= now_datetime:
                    continue
                if alert.is_acknowledged:
                    continue
                new_list.append( alert )

            removed_count = len(self._alert_list) - len(new_list)
            logger.debug( f'Removed "{removed_count}" alerts.' )
            if removed_count > 0:
                self._alert_list = new_list
                self._last_changed_datetime = datetimeproxy.now()

        finally:
            self._active_alerts_lock.release()
        return
    
    
