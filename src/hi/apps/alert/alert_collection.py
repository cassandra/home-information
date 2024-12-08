from datetime import datetime
import logging
import threading

import hi.apps.common.datetimeproxy as datetimeproxy

from .alarm import Alarm
from .alert import Alert
from .enums import AlarmLevel

logger = logging.getLogger(__name__)


class AlertCollection:

    MAX_ALERT_LIST_SIZE = 50
    
    def __init__(self):
        self._alert_list = list()
        self._active_alerts_lock = threading.Lock()
        self._last_changed_datetime = datetimeproxy.now()
        return

    def __bool__(self):
        return bool( self._alert_list )
    
    def __len__(self):
        return len( self._alert_list )
    
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
