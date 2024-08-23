import logging
import pyzm.api as zmapi

from hi.apps.common.singleton import Singleton

from hi.integrations.core.enums import IntegrationType
from hi.integrations.core.exceptions import IntegrationPropertyError
from hi.integrations.core.integration_manager import IntegrationManager

from .enums import ZmPropertyName

logger = logging.getLogger(__name__)


class ZoneMinderManager( Singleton ):

    def __init_singleton__( self ):
        self.zmClient = None
        self._is_loading = False
        return

    def initialize( self ):
        if self._is_loading:
            logger.warning( 'ZoneMinder initialization already started.' )
            return
        try:
            logger.debug( 'Loading ZoneMinder data ...' )
            self._is_loading = True
            self.zmClient = None
            zm_integration = IntegrationManager().get_integration( IntegrationType.ZONEMINDER )
            if not zm_integration.is_enabled:
                logger.debug( 'ZoneMinder integration is not enabled.' )
                return

            property_dict = zm_integration.property_dict
            for zm_prop_name in ZmPropertyName:
                zm_prop = property_dict.get( zm_prop_name.label )
                if not zm_prop:
                    raise IntegrationPropertyError( f'Missing ZM property {zm_prop_name.label}' ) 
                if zm_prop.is_required and not zm_prop.value.strip():
                    raise IntegrationPropertyError( f'Missing ZM property value for {zm_prop_name.label}' ) 
                    
                continue

            api_options = {
                'apiurl': property_dict.get( ZmPropertyName.API_URL.label ).value,
                'portalurl': property_dict.get( ZmPropertyName.PORTAL_URL.label ).value,
                'user': property_dict.get( ZmPropertyName.API_USER.label ).value,
                'password': property_dict.get( ZmPropertyName.API_PASSWORD.label ).value,
                # 'disable_ssl_cert_check': True
            }

            self.zmClient = zmapi.ZMApi(options=api_options)

            logger.debug("Getting ZM Monitors")
            ms = self.zmClient.monitors()
            for m in ms.list():
                logger.debug('Name:{} Enabled:{} Type:{} Dims:{}'.format( m.name(),
                                                                          m.enabled(),
                                                                          m.type(),
                                                                          m.dimensions()) )
                logger.debug( m.status() )

                # TODO: Add new cameras if needed
                
                continue
        
        finally:
            self._is_loading = False
            logger.debug( 'ZoneMinder initialization completed.' )
        return
