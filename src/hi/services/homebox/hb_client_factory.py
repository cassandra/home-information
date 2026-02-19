"""Factory for creating and testing HomeBox API clients."""

import logging
from typing import Dict

from hi.apps.system.enums import HealthStatusType
from hi.integrations.exceptions import IntegrationAttributeError
from hi.integrations.models import IntegrationAttribute
from hi.integrations.transient_models import IntegrationKey, IntegrationValidationResult

from .enums import HbAttributeType
from .hb_client.api import HBApi
from .hb_metadata import HbMetaData

logger = logging.getLogger(__name__)


class HbClientFactory:
    """Factory for creating and testing HomeBox API clients."""

    def create_client(
            self,
            hb_attr_type_to_attribute: Dict[HbAttributeType, IntegrationAttribute]) -> HBApi:
        """
        Create a HBApi client from integration attributes.

        Args:
            hb_attr_type_to_attribute: Dictionary mapping attribute types to attribute objects

        Returns:
            Configured HBApi instance

        Raises:
            IntegrationAttributeError: If required attributes are missing or invalid
        """
        # Build API data payload
        api_options = {
            # 'disable_ssl_cert_check': True
        }

        attr_to_api_option_key = {
            HbAttributeType.API_URL: 'apiurl',
            HbAttributeType.PORTAL_URL: 'portalurl',
            HbAttributeType.API_USER: 'user',
            HbAttributeType.API_PASSWORD: 'password',
        }

        integration_key_to_attribute = { x.integration_key: x
                                         for x in hb_attr_type_to_attribute.values() }

        for hb_attr_type in attr_to_api_option_key.keys():
            integration_key = IntegrationKey(
                integration_id=HbMetaData.integration_id,
                integration_name=str(hb_attr_type),
            )
            hb_attr = integration_key_to_attribute.get(integration_key)

            if not hb_attr:
                raise IntegrationAttributeError(
                    f'Missing HB API attribute {hb_attr_type}')
            if not hb_attr.value.strip():
                raise IntegrationAttributeError(
                    f'Missing HB API attribute value for {hb_attr_type}')

            options_key = attr_to_api_option_key[hb_attr_type]
            api_options[options_key] = hb_attr.value

        log_options = dict(api_options)
        if 'password' in log_options and log_options['password']:
            log_options['password'] = '***'

        logger.debug(f'HomeBox client options: {log_options}')
        return HBApi(options=api_options)

    def test_client(self, client: HBApi) -> IntegrationValidationResult:
        """
        Test API connectivity for a given client.

        Args:
            client: HBApi instance to test

        Returns:
            IntegrationValidationResult indicating success or failure with details
        """
        try:
            # Test basic API connectivity by fetching items
            items = client.items().list()
            if items is not None:
                # Successful API call
                return IntegrationValidationResult.success()
            else:
                return IntegrationValidationResult.error(
                    status=HealthStatusType.ERROR,
                    error_message='Failed to fetch items from HomeBox API'
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
                status = HealthStatusType.ERROR
                user_message = f'Authentication failed: {e}'
            elif any(keyword in error_msg for keyword in ['connect',
                                                          'network',
                                                          'timeout',
                                                          'unreachable',
                                                          'resolve',
                                                          'schema',
                                                          'url']):
                status = HealthStatusType.ERROR
                user_message = f'Cannot connect to HomeBox: {e}'
            else:
                status = HealthStatusType.WARNING
                user_message = f'API test failed: {e}'

            return IntegrationValidationResult.error(
                status=status,
                error_message=user_message
            )
        
