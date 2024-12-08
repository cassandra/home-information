from datetime import datetime
import logging

from hi.apps.common.singleton import Singleton

from .alert_collection import AlertCollection
from .alarm import Alarm
from .alert_status import AlertStatusData

logger = logging.getLogger(__name__)


class AlertManager(Singleton):

    def __init_singleton__(self):
        self._alert_collection = AlertCollection()
        return

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
        
        new_alert = self._alert_collection.get_most_important_alert(
            since_datetime = last_alert_status_datetime,
        )
        if new_alert:
            max_alert = new_alert.audio_signal_name if new_alert else None
        else:
            max_alert = self._alert_collection.get_most_important_alert()

        # TODO: Use this latest new alarm for providing auto-switching to
        # show something related to the latest event, e.g., camera feed.
        # This would be a suggestion to the console as it would decide
        # whether to show it based on the console settings and user
        # interaction context.
        #
        latest_new_alarm = self._alert_collection.get_most_recent_alarm(
            since_datetime = last_alert_status_datetime,
        )
        
        return AlertStatusData(
            alert_list = None,
            max_audio_signal = max_alert.audio_signal if max_alert else None,
            new_audio_signal = new_alert.audio_signal if new_alert else None,
        )
    
    async def add_alarm( self, alarm : Alarm ):
        logging.debug( f'Adding Alarm: {alarm}' )
        try:
            self._alert_collection.add_alarm()
        except ValueError as ve:
            logging.info( str(ve) )
        return
