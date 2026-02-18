import logging

from hi.apps.common.database_lock import ExclusionLockContext
from hi.apps.common.processing_result import ProcessingResult

from .hb_mixins import HomeBoxMixin

logger = logging.getLogger(__name__)


class HomeBoxSynchronizer( HomeBoxMixin ):

    SYNCHRONIZATION_LOCK_NAME = 'hb_integration_sync'

    def __init__(self):
        return

    def sync( self ) -> ProcessingResult:
        try:
            with ExclusionLockContext( name = self.SYNCHRONIZATION_LOCK_NAME ):
                logger.debug( 'HomeBox integration sync started.' )
                return self._sync_helper()
        except RuntimeError as e:
            logger.exception( e )
            return ProcessingResult(
                title = 'HomeBox Import Result',
                error_list = [ str(e) ],
            )
        finally:
            logger.debug( 'HomeBox integration sync ended.' )

    def _sync_helper( self ) -> ProcessingResult:
        hb_manager = self.hb_manager()
        result = ProcessingResult( title = 'HomeBox Import Result' )

        if not hb_manager.hb_client:
            logger.debug( 'HomeBox client not created. HomeBox integration disabled?' )
            result.error_list.append( 'Sync problem. HomeBox integration disabled?' )
            return result

        item_list = hb_manager.fetch_hb_items_from_api()
        result.message_list.append( f'Found {len(item_list)} current HomeBox items.' )

        return result
