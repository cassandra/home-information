import logging
import pyzm.api as pyzm_api

from hi.apps.common.database_lock import ExclusionLockContext
from hi.apps.common.processing_result import ProcessingResult
from hi.apps.common.singleton import Singleton

from hi.integrations.core.enums import IntegrationType
from hi.integrations.core.exceptions import IntegrationPropertyError
from hi.integrations.core.models import Integration

from .enums import ZmPropertyName

logger = logging.getLogger(__name__)


class ZoneMinderManager( Singleton ):

    SYNCHRONIZATION_LOCK_NAME = 'zm_integration_sync'

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
            self._zm_client = self.create_zm_client()
        
        finally:
            self._is_loading = False
            logger.debug( 'ZoneMinder loading completed.' )
        return

    def create_zm_client(self):
        try:
            zm_integration = Integration.objects.get( integration_type_str = str(IntegrationType.ZONEMINDER) )
        except Integration.DoesNotExist:
            logger.debug( 'ZoneMinder integration is not enabled.' )

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
        
    def sync( self ) -> ProcessingResult:
        try:
            with ExclusionLockContext( name = self.SYNCHRONIZATION_LOCK_NAME ):
                logger.debug( 'ZoneMinder integration sync started.' )
                return self._sync_helper()
        except RuntimeError as e:
            return ProcessingResult(
                title = 'ZM Sync Result',
                error_list = [ str(e) ],
            )
        finally:
            logger.debug( 'ZoneMinder integration sync ended.' )
    
    def _sync_helper( self ) -> ProcessingResult:
        processing_result = ProcessingResult( title = 'ZM Sync Result' )
        
        logger.debug( 'Getting ZM monitors.' )
        zm_client = self.zm_client
        if not zm_client:
            logger.debug( 'ZoneMinder client not created. ZM integration disabled?' )
            processing_result.error_list.append( 'Sync problem. ZM integration disabled?' )
            return processing_result
            
        ms = zm_client.monitors()
        for m in ms.list():
            
            logger.debug('Name:{} Enabled:{} Type:{} Dims:{}'.format( m.name(),
                                                                      m.enabled(),
                                                                      m.type(),
                                                                      m.dimensions()) )
            logger.debug( m.status() )

            # TODO: Add new cameras if needed

            continue
        return processing_result
