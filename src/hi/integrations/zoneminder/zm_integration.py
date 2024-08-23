import logging
import pyzm.api as pyzm_api

from hi.apps.common.database_lock import ExclusionLockContext

from hi.integrations.core.enums import IntegrationType
from hi.integrations.core.exceptions import IntegrationPropertyError
from hi.integrations.core.integration_manager import IntegrationManager

from .enums import ZmPropertyName

logger = logging.getLogger(__name__)


class ZoneMinderIntegration:

    SYNCHRONIZATION_LOCK_NAME = 'zm_integration_sync'

    @classmethod
    def create_zm_client(cls):

        zm_integration = IntegrationManager().get_integration( IntegrationType.ZONEMINDER )
        if not zm_integration.is_enabled:
            logger.debug( 'ZoneMinder integration is not enabled.' )
            return None

        # Verify integration
        property_dict = zm_integration.property_dict
        for zm_prop_name in ZmPropertyName:
            zm_prop = property_dict.get( zm_prop_name.name )
            if not zm_prop:
                raise IntegrationPropertyError( f'Missing ZM property {zm_prop_name.name}' ) 
            if zm_prop.is_required and not zm_prop.value.strip():
                raise IntegrationPropertyError( f'Missing ZM property value for {zm_prop_name.name}' ) 

            continue
        
        api_options = {
            'apiurl': property_dict.get( ZmPropertyName.API_URL.name ).value,
            'portalurl': property_dict.get( ZmPropertyName.PORTAL_URL.name ).value,
            'user': property_dict.get( ZmPropertyName.API_USER.name ).value,
            'password': property_dict.get( ZmPropertyName.API_PASSWORD.name ).value,
            # 'disable_ssl_cert_check': True
        }

        return pyzm_api.ZMApi( options = api_options )
        
    @classmethod
    def sync( cls ):
        try:
            with ExclusionLockContext( name = cls.SYNCHRONIZATION_LOCK_NAME ):
                logger.debug( 'ZoneMinder integration sync started.' )
                cls._sync_helper()
        except RuntimeError:
            pass
        finally:
            logger.debug( 'ZoneMinder integration sync ended.' )
        return
    
    @classmethod
    def _sync_helper( cls ):
        logger.debug( 'Getting ZM monitors.' )
        zm_client = cls.create_zm_client()
        if not zm_client:
            logger.debug( 'ZoneMinder client not created. ZM integration disabled?.' )
            return
            
        ms = zm_client.monitors()
        for m in ms.list():
            
            logger.debug('Name:{} Enabled:{} Type:{} Dims:{}'.format( m.name(),
                                                                      m.enabled(),
                                                                      m.type(),
                                                                      m.dimensions()) )
            logger.debug( m.status() )

            # TODO: Add new cameras if needed

            continue
        return
