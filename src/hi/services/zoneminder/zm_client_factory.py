"""Factory for creating and testing ZoneMinder API clients."""

import logging
from typing import Dict

from hi.apps.system.enums import HealthStatusType
from hi.integrations.exceptions import IntegrationAttributeError
from hi.integrations.models import IntegrationAttribute
from hi.integrations.transient_models import IntegrationKey, IntegrationValidationResult

from .enums import ZmAttributeType
from .pyzm_client.api import ZMApi
from .zm_metadata import ZmMetaData

logger = logging.getLogger(__name__)


class ZmClientFactory:
    """Factory for creating and testing ZoneMinder API clients."""

    def create_client(
            self,
            zm_attr_type_to_attribute: Dict[ZmAttributeType, IntegrationAttribute]) -> ZMApi:
        """
        Create a ZMApi client from integration attributes.

        Args:
            zm_attr_type_to_attribute: Dictionary mapping attribute types to attribute objects

        Returns:
            Configured ZMApi instance

        Raises:
            IntegrationAttributeError: If required attributes are missing or invalid
        """
        # Build API data payload
        api_options = {
            # 'disable_ssl_cert_check': True
        }

        attr_to_api_option_key = {
            ZmAttributeType.API_URL: 'apiurl',
            ZmAttributeType.PORTAL_URL: 'portalurl',
            ZmAttributeType.API_USER: 'user',
            ZmAttributeType.API_PASSWORD: 'password',
        }

        integration_key_to_attribute = { x.integration_key: x
                                         for x in zm_attr_type_to_attribute.values() }

        for zm_attr_type in attr_to_api_option_key.keys():
            integration_key = IntegrationKey(
                integration_id=ZmMetaData.integration_id,
                integration_name=str(zm_attr_type),
            )
            zm_attr = integration_key_to_attribute.get(integration_key)

            if not zm_attr:
                raise IntegrationAttributeError(
                    f'Missing ZM API attribute {zm_attr_type}')
            if not zm_attr.value.strip():
                raise IntegrationAttributeError(
                    f'Missing ZM API attribute value for {zm_attr_type}')

            options_key = attr_to_api_option_key[zm_attr_type]
            api_options[options_key] = zm_attr.value

        logger.debug(f'ZoneMinder client options: {api_options}')
        return ZMApi(options=api_options)

    def test_client(self, client: ZMApi) -> IntegrationValidationResult:
        """
        Test API connectivity for a given client.

        Args:
            client: ZMApi instance to test

        Returns:
            IntegrationValidationResult indicating success or failure with details
        """
        try:
            # Test basic API connectivity by fetching states
            states = client.states().list()
            if states is not None:
                # Successful API call
                return IntegrationValidationResult.success()
            else:
                return IntegrationValidationResult.error(
                    status=HealthStatusType.CONNECTION_ERROR,
                    error_message='Failed to fetch states from ZoneMinder API'
                )

        except Exception as e:
            error_msg = str(e).lower()

            # Categorize common error types for better user feedback
            if any(keyword in error_msg for keyword in ['auth',
                                                        'unauthorized',
                                                        'forbidden',
                                                        'login',
                                                        'credential',
                                                        'password']):
                status = HealthStatusType.CONNECTION_ERROR
                user_message = f'Authentication failed: {e}'
            elif any(keyword in error_msg for keyword in ['connect',
                                                          'network',
                                                          'timeout',
                                                          'unreachable',
                                                          'resolve',
                                                          'schema',
                                                          'url']):
                status = HealthStatusType.CONNECTION_ERROR
                user_message = f'Cannot connect to ZoneMinder: {e}'
            else:
                status = HealthStatusType.TEMPORARY_ERROR
                user_message = f'API test failed: {e}'

            return IntegrationValidationResult.error(
                status=status,
                error_message=user_message
            )
        
