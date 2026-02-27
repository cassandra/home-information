import logging
from asgiref.sync import sync_to_async
from typing import Dict, List

from hi.apps.common.singleton_manager import SingletonManager
from hi.apps.system.aggregate_health_provider import AggregateHealthProvider
from hi.apps.system.api_health_status_provider import ApiHealthStatusProvider
from hi.apps.system.provider_info import ProviderInfo
from hi.apps.system.enums import HealthStatusType

from hi.integrations.exceptions import (
    IntegrationAttributeError,
    IntegrationError,
    IntegrationDisabledError,
)
from hi.integrations.transient_models import (
    IntegrationKey,
    IntegrationValidationResult,
)
from hi.integrations.models import Integration, IntegrationAttribute

from .enums import HbAttributeType
from .hb_client.api import HBApi
from .hb_client_factory import HbClientFactory
from .hb_metadata import HbMetaData

logger = logging.getLogger(__name__)


class HomeBoxManager( SingletonManager, AggregateHealthProvider, ApiHealthStatusProvider ):

    def __init_singleton__( self ):
        super().__init_singleton__()

        self._hb_attr_type_to_attribute = dict()
        self._hb_client = None
        self._client_factory = HbClientFactory()

        self._hb_items_list = list()

        self._change_listeners = set()

        self.add_api_health_status_provider(self)

        return

    @classmethod
    def get_provider_info(cls) -> ProviderInfo:
        return ProviderInfo(
            provider_id = 'hi.services.homebox.manager',
            provider_name = 'HomeBox Integration',
            description = '',
        )

    @classmethod
    def get_api_provider_info(cls) -> ProviderInfo:
        return ProviderInfo(
            provider_id = 'hi.services.homebox.api',
            provider_name = 'HomeBox API',
            description = 'HomeBox REST API',
        )

    def register_change_listener( self, callback ):
        if callback not in self._change_listeners:
            logger.debug( f'Adding HomeBox setting change listener from {callback.__module__}' )
            self._change_listeners.add( callback )
        else:
            logger.debug( f'HomeBox setting change listener from'
                          f' {callback.__module__} already registered, skipping duplicate' )
        return

    def notify_settings_changed(self):
        self.reload()
        for callback in self._change_listeners:
            try:
                callback()
            except Exception:
                logger.exception( 'Problem calling setting change callback.' )
            continue
        return

    @property
    def hb_client(self) -> HBApi:
        return self._hb_client

    def _reload_implementation( self ):
        try:
            self._hb_attr_type_to_attribute = self._load_attributes()
            self._hb_client = self.create_hb_client( self._hb_attr_type_to_attribute )
            self.clear_caches()
            self.record_healthy('Reloaded')

        except IntegrationDisabledError:
            msg = 'HomeBox integration disabled'
            logger.info(msg)
            self.record_disabled( msg )

        except IntegrationError as e:
            error_msg = f'HomeBox integration configuration error: {e}'
            logger.error(error_msg)
            self.record_error( f'Configuration error: {error_msg}' )

        except IntegrationAttributeError as e:
            error_msg = f'HomeBox integration attribute error: {e}'
            logger.error(error_msg)
            self.record_error( f'Configuration error: {error_msg}' )

        except Exception as e:
            error_msg = f'Unexpected error loading HomeBox configuration: {e}'
            logger.exception(error_msg)
            self.record_warning( f'Temporary issue: {error_msg}' )
        return

    def clear_caches(self):
        self._hb_items_list = list()
        self._hb_labels_list = list()
        self._hb_locations_list = list()
        self._hb_maintenances_list = list()
        return

    def _load_attributes(self) -> Dict[ HbAttributeType, IntegrationAttribute ]:
        try:
            hb_integration = Integration.objects.get( integration_id = HbMetaData.integration_id )
        except Integration.DoesNotExist:
            raise IntegrationError( 'HomeBox integration is not implemented.' )

        if not hb_integration.is_enabled:
            raise IntegrationDisabledError( 'HomeBox integration is not enabled.' )

        integration_attributes = list(hb_integration.attributes.all())
        return self._build_hb_attr_type_to_attribute_map(
            integration_attributes = integration_attributes,
            enforce_requirements = True,
        )

    def create_hb_client(
            self,
            hb_attr_type_to_attribute : Dict[ HbAttributeType, IntegrationAttribute ] ) -> HBApi:
        return self._client_factory.create_client(hb_attr_type_to_attribute)

    def fetch_hb_items_from_api( self, verbose : bool = True ) -> list:
        if verbose:
            logger.debug( 'Getting current HomeBox items.' )

        if not self.hb_client:
            logger.warning('HomeBox client not available - cannot fetch items')
            return []

        with self.api_call_context( 'hb_items' ):
            options = {
                'force_reload': True,
            }
            return self.hb_client.items().list()

    async def fetch_hb_items_from_api_async( self, verbose : bool = True ) -> list:
        return await sync_to_async(
            self.fetch_hb_items_from_api,
            thread_sensitive = True,
        )(verbose=verbose)
    
    def test_connection(self) -> bool:
        try:
            if not self.hb_client:
                self.record_error('HomeBox client not configured')
                return False

            items = self.fetch_hb_items_from_api(verbose=False)
            if items is not None:
                self.record_healthy('OK')
                return True

            self.record_error('Failed to fetch items from HomeBox API')
            return False

        except Exception as e:
            error_msg = f'Connection test failed: {e}'
            logger.debug(error_msg)
            self.record_error( f'Connection error: {error_msg}' )
            return False

    def test_client_with_attributes(
            self,
            hb_attr_type_to_attribute: Dict[HbAttributeType, IntegrationAttribute]
    ) -> IntegrationValidationResult:
        try:
            temp_client = self._client_factory.create_client(hb_attr_type_to_attribute)
            return self._client_factory.test_client(temp_client)

        except IntegrationError as e:
            return IntegrationValidationResult.error(
                status=HealthStatusType.ERROR,
                error_message=str(e),
            )
        except IntegrationAttributeError as e:
            return IntegrationValidationResult.error(
                status=HealthStatusType.ERROR,
                error_message=str(e),
            )

    def validate_configuration(
            self,
            integration_attributes: List[IntegrationAttribute]) -> IntegrationValidationResult:
        try:
            hb_attr_type_to_attribute = self._build_hb_attr_type_to_attribute_map(
                integration_attributes = integration_attributes,
                enforce_requirements = False,
            )
            return self.test_client_with_attributes(hb_attr_type_to_attribute)

        except Exception as e:
            logger.exception(f'Error in HomeBox configuration validation: {e}')
            return IntegrationValidationResult.error(
                status=HealthStatusType.WARNING,
                error_message=f'Configuration validation failed: {e}'
            )

    def _build_hb_attr_type_to_attribute_map(
            self,
            integration_attributes: List[IntegrationAttribute],
            enforce_requirements: bool = True) -> Dict[HbAttributeType, IntegrationAttribute]:
        hb_attr_type_to_attribute = {}
        integration_key_to_attribute = {attr.integration_key: attr for attr in integration_attributes}

        for hb_attr_type in HbAttributeType:
            integration_key = IntegrationKey(
                integration_id = HbMetaData.integration_id,
                integration_name = str(hb_attr_type),
            )
            hb_attr = integration_key_to_attribute.get(integration_key)

            if not hb_attr:
                if enforce_requirements and hb_attr_type.is_required:
                    raise IntegrationAttributeError(f'Missing HomeBox attribute {hb_attr_type}')
                continue

            if enforce_requirements and hb_attr.is_required and not hb_attr.value.strip():
                raise IntegrationAttributeError(
                    f'Missing HomeBox attribute value for {hb_attr_type}')

            hb_attr_type_to_attribute[hb_attr_type] = hb_attr

        return hb_attr_type_to_attribute