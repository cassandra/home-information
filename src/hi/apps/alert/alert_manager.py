import logging

from hi.apps.common.singleton import Singleton

from .transient_models import Alarm

logger = logging.getLogger(__name__)


class AlertManager(Singleton):

    def __init_singleton__(self):
        return

    async def add_alarm( self, alarm : Alarm ):
        logging.debug( f'Alarm added: {alarm}' )
        logging.error( '\n\n\nIMPLEMENT ME! AlertManager.add_alarm()\n\n' )
        return
    
