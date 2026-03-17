from unittest.mock import Mock

from django.test import TestCase

from hi.apps.attribute.enums import AttributeValueType
from hi.integrations.enums import IntegrationAttributeType
from hi.integrations.initializers import IntegrationInitializer
from hi.integrations.integration_gateway import IntegrationGateway
from hi.integrations.models import Integration, IntegrationAttribute
from hi.integrations.transient_models import IntegrationMetaData


class MockIntegrationAttributeType(IntegrationAttributeType):
    TEST_ATTR = ('Test Attribute', 'Test description', AttributeValueType.TEXT, {}, True, True, 'default')


class MockIntegrationGateway(IntegrationGateway):
    def __init__(self, integration_id='test_integration', label='Test Integration'):
        self.integration_id = integration_id
        self.label = label

    def get_metadata(self):
        return IntegrationMetaData(
            integration_id=self.integration_id,
            label=self.label,
            attribute_type=MockIntegrationAttributeType,
            allow_entity_deletion=True,
        )

    def get_manage_view_pane(self):
        return Mock()

    def get_monitor(self):
        return Mock()

    def get_controller(self):
        return Mock()


class IntegrationInitializerTestCase(TestCase):

    def test_run_creates_missing_integration_and_attributes(self):
        initializer = IntegrationInitializer()

        gateway = MockIntegrationGateway('test_integration')
        initializer._create_integrations(
            defined_integration_gateway_map={'test_integration': gateway},
        )

        integration = Integration.objects.get(integration_id='test_integration')
        self.assertFalse(integration.is_enabled)
        self.assertEqual(integration.attributes.count(), 1)

    def test_run_is_idempotent(self):
        initializer = IntegrationInitializer()

        gateway = MockIntegrationGateway('test_integration')
        initializer._create_integrations(
            defined_integration_gateway_map={'test_integration': gateway},
        )
        initializer._create_integrations(
            defined_integration_gateway_map={'test_integration': gateway},
        )

        self.assertEqual(Integration.objects.filter(integration_id='test_integration').count(), 1)
        self.assertEqual(IntegrationAttribute.objects.count(), 1)
