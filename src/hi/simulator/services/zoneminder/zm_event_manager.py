from datetime import datetime
import threading
from typing import Dict, List

from hi.apps.common.singleton import Singleton

from .sim_models import ZmSimEvent, ZmSimMonitor
from .zm_event_history import ZmSimEventHistory


class ZmSimEventManager( Singleton ):
    
    def __init_singleton__( self ):
        self._zm_sim_events_map : Dict[ int, ZmSimEventHistory ] = dict()
        self._data_lock = threading.Lock()
        return

    def add_motion_value( self,
                          zm_sim_monitor : ZmSimMonitor,
                          motion_value   : bool ):
        self._data_lock.acquire()
        try:
            monitor_id = zm_sim_monitor.monitor_id
            if monitor_id not in self._zm_sim_events_map:
                self._zm_sim_events_map[monitor_id] = ZmSimEventHistory(
                    zm_sim_monitor = zm_sim_monitor,
                )
            self._zm_sim_events_map[monitor_id].add_motion_value( motion_value = motion_value )
        finally:
            self._data_lock.release()
        return

    def get_events_by_start_datetime( self, start_datetime : datetime ) -> List[ ZmSimEvent ]:
        zm_sim_event_list = list()
        for zm_event_history in self._zm_sim_events_map.values():
            event_list = zm_event_history.get_events_by_start_datetime( start_datetime = start_datetime )
            zm_sim_event_list.extend( event_list )
            continue
        self._update_zm_sim_events( zm_sim_event_list = zm_sim_event_list )
        return zm_sim_event_list

    def _update_zm_sim_events( self, zm_sim_event_list : List[ ZmSimEvent ] ):
        for zm_sim_event in zm_sim_event_list:
            if zm_sim_event.is_active:
                zm_sim_event.update_score_properties()
            continue
        return
