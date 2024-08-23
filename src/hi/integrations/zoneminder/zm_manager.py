import logging

from hi.apps.common.singleton import Singleton

from .zm_integration import ZoneMinderIntegration

logger = logging.getLogger(__name__)


class ZoneMinderManager( Singleton ):

    def __init_singleton__( self ):
        self._is_loading = False
        self._zm_client = None
        self.reload()
        return

    @property
    def zm_client(self):
        return self._zm_client
    
    def reload( self ):
        if self._is_loading:
            logger.warning( 'ZoneMinder is already loading.' )
            return
        try:
            self._is_loading = True
            self._zm_client = ZoneMinderIntegration.create_zm_client()
        
        finally:
            self._is_loading = False
            logger.debug( 'ZoneMinder loading completed.' )
        return
