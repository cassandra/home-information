from asgiref.sync import sync_to_async
import logging
import traceback

from hi.integrations.zoneminder.zm_integration import ZoneMinderIntegration

logger = logging.getLogger(__name__)


async def initialize_integrations():
    """
    Each integration should:
    - run asynchronously;
    - check if they are enabled or not; and
    - sanity check their configuration properties.
    """
    try:
        await sync_to_async( ZoneMinderIntegration().sync)()  # Need wrapper for ORM operations
    except Exception as e:
        logger.error( 'ZM sync error: {}'.format(str(e)) )
        logger.info( traceback.format_exc() )

    # Add other integration initializations here.

    return
