"""Factory for creating and testing Home Assistant API clients."""

import logging
from typing import Dict

from hi.integrations.exceptions import IntegrationAttributeError
from hi.integrations.enums import IntegrationHealthStatusType
from hi.integrations.models import IntegrationAttribute
from hi.integrations.transient_models import IntegrationKey, IntegrationValidationResult

from .enums import HassAttributeType
from .hass_client import HassClient
from .hass_metadata import HassMetaData

logger = logging.getLogger(__name__)


class HassClientFactory:
    """Factory for creating and testing Home Assistant API clients."""

    def create_client(
            self,
            hass_attr_type_to_attribute: Dict[HassAttributeType, IntegrationAttribute]) -> HassClient:
        """
        Create a HassClient from integration attributes.

        Args:
            hass_attr_type_to_attribute: Dictionary mapping attribute types to attribute objects

        Returns:
            Configured HassClient instance

        Raises:
            IntegrationAttributeError: If required attributes are missing or invalid
        """
        # Build API data payload
        api_options = {
            # 'disable_ssl_cert_check': True
        }

        attr_to_api_option_key = {
            HassAttributeType.API_BASE_URL: HassClient.API_BASE_URL,
            HassAttributeType.API_TOKEN: HassClient.API_TOKEN,
        }

        integration_key_to_attribute = { x.integration_key: x
                                         for x in hass_attr_type_to_attribute.values() }

        for hass_attr_type in attr_to_api_option_key.keys():
            integration_key = IntegrationKey(
                integration_id=HassMetaData.integration_id,
                integration_name=str(hass_attr_type),
            )
            hass_attr = integration_key_to_attribute.get(integration_key)

            if not hass_attr:
                raise IntegrationAttributeError(
                    f'Missing HASS API attribute {hass_attr_type}')
            if not hass_attr.value.strip():
                raise IntegrationAttributeError(
                    f'Missing HASS API attribute value for {hass_attr_type}')

            options_key = attr_to_api_option_key[hass_attr_type]
            api_options[options_key] = hass_attr.value

        logger.debug(f'Home Assistant client options: {api_options}')
        return HassClient(api_options=api_options)

    def test_client(self, client: HassClient) -> IntegrationValidationResult:
        """
        Test API connectivity for a given client.

        Args:
            client: HassClient instance to test

        Returns:
            IntegrationValidationResult indicating success or failure with details
        """
        try:
            # Test basic API connectivity
            states = client.states()
            if states is not None:
                # Successful API call
                return IntegrationValidationResult.success()
            else:
                return IntegrationValidationResult.error(
                    status=IntegrationHealthStatusType.CONNECTION_ERROR,
                    error_message='Failed to fetch states from Home Assistant API'
                )

        except Exception as e:
            error_msg = str(e).lower()

            # Categorize common error types for better user feedback
            if any(keyword in error_msg for keyword in ['auth',
                                                        'unauthorized',
                                                        'forbidden',
                                                        'token',
                                                        'credential']):
                status = IntegrationHealthStatusType.CONNECTION_ERROR
                user_message = f'Authentication failed: {e}'
            elif any(keyword in error_msg for keyword in ['connect',
                                                          'network',
                                                          'timeout',
                                                          'unreachable',
                                                          'resolve']):
                status = IntegrationHealthStatusType.CONNECTION_ERROR
                user_message = f'Cannot connect to Home Assistant: {e}'
            else:
                status = IntegrationHealthStatusType.TEMPORARY_ERROR
                user_message = f'API test failed: {e}'

            return IntegrationValidationResult.error(
                status=status,
                error_message=user_message
            )
        
