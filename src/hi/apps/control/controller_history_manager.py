import logging

from hi.apps.common.singleton import Singleton

from .models import Controller, ControllerHistory

logger = logging.getLogger(__name__)


class ControllerHistoryManager( Singleton ):

    def __init_singleton__( self ):
        return

    def add_to_controller_history( self, controller : Controller, value : str ):
        if not controller.persist_history:
            return

        return ControllerHistory.objects.create(
            controller = controller,
            value = value,
        )
