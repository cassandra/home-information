"""
Synthetic data generators for ZoneMinder testing.

Provides centralized, reusable test data creation following the project's
synthetic data pattern. Creates real Django ORM objects for testing.
"""

import uuid
from typing import Tuple, List

from hi.integrations.models import Integration, IntegrationAttribute
from hi.integrations.transient_models import IntegrationKey

from hi.services.zoneminder.enums import ZmAttributeType
from hi.services.zoneminder.zm_metadata import ZmMetaData


class ZoneMinderSyntheticData:
    """Centralized synthetic data generators for ZoneMinder testing."""

    @staticmethod
    def create_zm_integration(is_enabled: bool = True) -> Integration:
        """Create a ZoneMinder integration with reasonable defaults."""
        return Integration.objects.create(
            integration_id=ZmMetaData.integration_id,
            is_enabled=is_enabled
        )

    @staticmethod
    def create_zm_attribute(
        integration: Integration,
        attribute_type: ZmAttributeType,
        value: str
    ) -> IntegrationAttribute:
        """Create a ZoneMinder integration attribute."""
        integration_key = IntegrationKey(
            integration_id=ZmMetaData.integration_id,
            integration_name=str(attribute_type)
        )

        return IntegrationAttribute.objects.create(
            integration=integration,
            integration_key_str=str(integration_key),
            value=value,
            is_required=attribute_type.is_required
        )

    @staticmethod
    def create_complete_zm_integration(is_enabled: bool = True) -> Tuple[Integration, List[IntegrationAttribute]]:
        """Create a complete ZoneMinder integration with all required attributes."""
        # Create the integration
        integration = ZoneMinderSyntheticData.create_zm_integration(is_enabled=is_enabled)

        # Create all required attributes with realistic values
        attributes = []

        # API URL - required
        attributes.append(ZoneMinderSyntheticData.create_zm_attribute(
            integration, ZmAttributeType.API_URL, 'https://zm.test.com/api'
        ))

        # Portal URL - required
        attributes.append(ZoneMinderSyntheticData.create_zm_attribute(
            integration, ZmAttributeType.PORTAL_URL, 'https://zm.test.com'
        ))

        # API User - required
        attributes.append(ZoneMinderSyntheticData.create_zm_attribute(
            integration, ZmAttributeType.API_USER, 'testuser'
        ))

        # API Password - required
        attributes.append(ZoneMinderSyntheticData.create_zm_attribute(
            integration, ZmAttributeType.API_PASSWORD, 'testpassword'
        ))

        # Timezone - required with default
        attributes.append(ZoneMinderSyntheticData.create_zm_attribute(
            integration, ZmAttributeType.TIMEZONE, 'America/Chicago'
        ))

        return integration, attributes

    @staticmethod
    def create_minimal_zm_integration() -> Tuple[Integration, List[IntegrationAttribute]]:
        """Create ZoneMinder integration with only absolutely required attributes."""
        integration = ZoneMinderSyntheticData.create_zm_integration()

        attributes = []

        # Only create the minimum required attributes
        attributes.append(ZoneMinderSyntheticData.create_zm_attribute(
            integration, ZmAttributeType.API_URL, 'https://zm.minimal.com/api'
        ))

        attributes.append(ZoneMinderSyntheticData.create_zm_attribute(
            integration, ZmAttributeType.PORTAL_URL, 'https://zm.minimal.com'
        ))

        attributes.append(ZoneMinderSyntheticData.create_zm_attribute(
            integration, ZmAttributeType.API_USER, 'minimaluser'
        ))

        attributes.append(ZoneMinderSyntheticData.create_zm_attribute(
            integration, ZmAttributeType.API_PASSWORD, 'minimalpass'
        ))

        return integration, attributes

    @staticmethod
    def create_zm_integration_with_optional_attributes() -> Tuple[Integration, List[IntegrationAttribute]]:
        """Create ZoneMinder integration including optional attributes."""
        integration, attributes = ZoneMinderSyntheticData.create_complete_zm_integration()

        # Add optional attributes
        attributes.append(ZoneMinderSyntheticData.create_zm_attribute(
            integration, ZmAttributeType.ADD_ALARM_EVENTS, 'true'
        ))

        return integration, attributes

    @staticmethod
    def create_invalid_zm_integration() -> Tuple[Integration, List[IntegrationAttribute]]:
        """Create ZoneMinder integration with invalid attribute values for testing."""
        integration = ZoneMinderSyntheticData.create_zm_integration()

        attributes = []

        # Create attributes with invalid values
        attributes.append(ZoneMinderSyntheticData.create_zm_attribute(
            integration, ZmAttributeType.API_URL, 'not-a-valid-url'
        ))

        attributes.append(ZoneMinderSyntheticData.create_zm_attribute(
            integration, ZmAttributeType.PORTAL_URL, 'also-not-valid'
        ))

        attributes.append(ZoneMinderSyntheticData.create_zm_attribute(
            integration, ZmAttributeType.API_USER, ''  # Empty user
        ))

        attributes.append(ZoneMinderSyntheticData.create_zm_attribute(
            integration, ZmAttributeType.API_PASSWORD, ''  # Empty password
        ))

        return integration, attributes

    @staticmethod
    def create_zm_integration_missing_required() -> Tuple[Integration, List[IntegrationAttribute]]:
        """Create ZoneMinder integration missing required attributes for error testing."""
        integration = ZoneMinderSyntheticData.create_zm_integration()

        attributes = []

        # Only create some required attributes, missing others
        attributes.append(ZoneMinderSyntheticData.create_zm_attribute(
            integration, ZmAttributeType.API_URL, 'https://zm.partial.com/api'
        ))

        attributes.append(ZoneMinderSyntheticData.create_zm_attribute(
            integration, ZmAttributeType.PORTAL_URL, 'https://zm.partial.com'
        ))

        # Missing API_USER and API_PASSWORD intentionally

        return integration, attributes

    @staticmethod
    def create_multiple_zm_integrations() -> List[Integration]:
        """Create multiple ZoneMinder integrations for multi-instance testing."""
        integrations = []

        # Create multiple integrations with different configurations
        for i in range(3):
            unique_id = str(uuid.uuid4())[:8]
            integration = Integration.objects.create(
                integration_id=f'zm_{unique_id}',
                is_enabled=True
            )

            # Add basic required attributes
            ZoneMinderSyntheticData.create_zm_attribute(
                integration, ZmAttributeType.API_URL, f'https://zm{i+1}.test.com/api'
            )
            ZoneMinderSyntheticData.create_zm_attribute(
                integration, ZmAttributeType.PORTAL_URL, f'https://zm{i+1}.test.com'
            )
            ZoneMinderSyntheticData.create_zm_attribute(
                integration, ZmAttributeType.API_USER, f'user{i+1}'
            )
            ZoneMinderSyntheticData.create_zm_attribute(
                integration, ZmAttributeType.API_PASSWORD, f'pass{i+1}'
            )

            integrations.append(integration)

        return integrations

    @staticmethod
    def create_attribute_mapping_dict(attributes: List[IntegrationAttribute]) -> dict:
        """Convert list of IntegrationAttributes to ZmAttributeType mapping dict."""
        mapping = {}

        for attr in attributes:
            # Parse the attribute type from the integration key
            attr_type = ZmAttributeType.from_name_safe(attr.integration_key.integration_name)
            if attr_type:
                mapping[attr_type] = attr

        return mapping

    @staticmethod
    def create_test_zm_states_data() -> List[dict]:
        """Create test ZoneMinder states data for API response mocking."""
        return [
            {
                'State': {
                    'Id': '1',
                    'Name': 'default',
                    'Definition': '[{"Id":"1","Function":"Monitor"},{"Id":"2","Function":"Modect"}]'
                }
            },
            {
                'State': {
                    'Id': '2',
                    'Name': 'alert',
                    'Definition': '[{"Id":"1","Function":"Modect"},{"Id":"2","Function":"Record"}]'
                }
            }
        ]

    @staticmethod
    def create_test_zm_monitors_data() -> List[dict]:
        """Create test ZoneMinder monitors data for API response mocking."""
        return [
            {
                'Monitor': {
                    'Id': '1',
                    'Name': 'Front Door',
                    'Function': 'Modect',
                    'Enabled': '1',
                    'Type': 'Remote',
                    'Host': '192.168.1.100',
                    'Path': '/videostream.cgi',
                }
            },
            {
                'Monitor': {
                    'Id': '2',
                    'Name': 'Back Yard',
                    'Function': 'Monitor',
                    'Enabled': '1',
                    'Type': 'Remote',
                    'Host': '192.168.1.101',
                    'Path': '/videostream.cgi',
                }
            }
        ]

    @staticmethod
    def create_test_zm_events_data() -> List[dict]:
        """Create test ZoneMinder events data for API response mocking."""
        return [
            {
                'Event': {
                    'Id': '1001',
                    'MonitorId': '1',
                    'Name': 'Motion Detection',
                    'Cause': 'Motion',
                    'StartTime': '2023-01-01 10:00:00',
                    'EndTime': '2023-01-01 10:00:30',
                    'Length': '30.00',
                    'Frames': '150',
                    'AlarmFrames': '15'
                }
            },
            {
                'Event': {
                    'Id': '1002',
                    'MonitorId': '2',
                    'Name': 'Object Detection',
                    'Cause': 'Motion',
                    'StartTime': '2023-01-01 11:00:00',
                    'EndTime': '2023-01-01 11:01:00',
                    'Length': '60.00',
                    'Frames': '300',
                    'AlarmFrames': '25'
                }
            }
        ]
    
