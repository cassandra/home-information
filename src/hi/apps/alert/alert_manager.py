from datetime import datetime
import logging

from hi.apps.common.singleton import Singleton
from hi.apps.console.transient_view_manager import TransientViewManager
from hi.apps.security.security_mixins import SecurityMixin
from hi.apps.notify.notify_mixins import NotificationMixin

from .alert import Alert
from .alert_queue import AlertQueue
from .alarm import Alarm
from .alert_status import AlertStatusData

logger = logging.getLogger(__name__)


class AlertManager( Singleton, NotificationMixin, SecurityMixin ):

    def __init_singleton__(self):
        self._alert_queue = AlertQueue()
        self._was_initialized = False
        return

    def ensure_initialized(self):
        if self._was_initialized:
            return
        # Any future heavyweight initializations go here (e.g., any DB operations).
        self._was_initialized = True
        return

    @property
    def unacknowledged_alert_list(self):
        return self._alert_queue.unacknowledged_alert_list

    def get_alert( self, alert_id : str ) -> Alert:
        return self._alert_queue.get_alert( alert_id = alert_id )

    def get_alert_status_data( self, last_alert_status_datetime : datetime ) -> AlertStatusData:
        
        # Things to check on alert status:
        #
        #   1) Has the alert list changed in any way? If so, return new HTML
        #      Note that the alert list could be empty, but still could be
        #      different from last time.
        #
        #   2) Has a new alert been added?  If so, tell the client so it
        #      can signal the user (audible).
        #
        #   3) What is the most critical alert in the list?  This is sent
        #      to the client so it can periodically re-notify that there are
        #      unacknowledged events.
        #
        # Because the alerts display their age, we always return the html
        # for the alert list if it is not empty so those ages can refresh
        # in the view. Also, we return it if it has changed, which include
        # it having become empty.
        
        new_alert = self._alert_queue.get_most_important_unacknowledged_alert(
            since_datetime = last_alert_status_datetime,
        )
        logger.debug(f"🔍 new_alert from queue: {new_alert}")
        
        if new_alert:
            max_alert = new_alert
        else:
            max_alert = self._alert_queue.get_most_important_unacknowledged_alert()
        
        logger.debug(f"🔍 max_alert from queue: {max_alert}")

        # Delegate auto-view decisions to TransientViewManager
        # If there's a new alert, consider it for auto-view switching
        if new_alert:
            TransientViewManager().consider_alert_for_auto_view(new_alert)
        
        return AlertStatusData(
            alert_list = self._alert_queue.unacknowledged_alert_list,
            max_audio_signal = max_alert.audio_signal if max_alert else None,
            new_audio_signal = new_alert.audio_signal if new_alert else None,
        )

    def acknowledge_alert( self, alert_id : str ):
        self._alert_queue.acknowledge_alert( alert_id = alert_id )
        return
    
    async def add_alarm( self, alarm : Alarm ):
        notification_manager = await self.notification_manager_async()
        if not notification_manager:
            return
        logging.debug( f'Adding Alarm: {alarm}' )
        security_state = self.security_manager().security_state
        try:
            alert = self._alert_queue.add_alarm( alarm = alarm )
            if security_state.uses_notifications and alert.has_single_alarm:
                notification_manager.add_notification_item(
                    notification_item = alert.to_notification_item(),
                )
        except ValueError as ve:
            logging.info( str(ve) )
        except Exception as e:
            logger.exception( 'Problem adding alarm to alert queue.', e )
        return
    
    async def do_periodic_maintenance(self):
        try:
            self._alert_queue.remove_expired_or_acknowledged_alerts()
        except Exception as e:
            logger.exception( 'Problem doing periodic alert maintenance.', e )
        return

