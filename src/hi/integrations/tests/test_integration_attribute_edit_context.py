"""
Unit tests for IntegrationAttributeItemEditContext capability filtering.
"""

import logging

from django.test import TestCase

from hi.apps.attribute.enums import AttributeValueType
from hi.integrations.connect.integration_attribute_edit_context import (
    IntegrationAttributeItemEditContext,
)
from hi.integrations.connect.integration_data import IntegrationData
from hi.integrations.connect.integration_gateway import IntegrationGateway
from hi.integrations.enums import (
    ALL_CAPABILITIES,
    IntegrationAttributeType,
    IntegrationCapability,
)
from hi.integrations.models import Integration, IntegrationAttribute
from hi.integrations.transient_models import (
    ConnectionTestResult,
    IntegrationKey,
    IntegrationMetaData,
)

logging.disable(logging.CRITICAL)


class MixedCapAttributeType(IntegrationAttributeType):
    """AttributeType with one member per capability shape (Connect-only,
    Import-only, both)."""

    CONNECT_FIELD = (
        'Connect Field', '', AttributeValueType.TEXT, None, True, True, '',
        frozenset({ IntegrationCapability.CONNECT }),
    )
    IMPORT_FIELD = (
        'Import Field', '', AttributeValueType.TEXT, None, True, True, '',
        frozenset({ IntegrationCapability.IMPORT }),
    )
    SHARED_FIELD = (
        'Shared Field', '', AttributeValueType.TEXT, None, True, True, '',
        ALL_CAPABILITIES,
    )


class _MixedCapGateway(IntegrationGateway):

    INTEGRATION_ID = 'mixed_cap'

    def get_metadata(self):
        return IntegrationMetaData(
            integration_id=self.INTEGRATION_ID,
            label='Mixed Cap',
            attribute_type=MixedCapAttributeType,
            allow_entity_deletion=True,
            capabilities=ALL_CAPABILITIES,
        )

    def validate_access(self, integration_attributes, timeout_secs):
        return ConnectionTestResult.success()


class CapabilityFilteredFormsetTests(TestCase):

    def setUp(self):
        self.integration = Integration.objects.create(
            integration_id=_MixedCapGateway.INTEGRATION_ID,
            is_enabled=True,
        )
        for member in MixedCapAttributeType:
            IntegrationAttribute.objects.create(
                integration=self.integration,
                name=member.label,
                value='',
                value_type_str=str(member.value_type),
                integration_key_str=IntegrationKey(
                    integration_id=self.integration.integration_id,
                    integration_name=str(member),
                ).integration_key_str,
            )
        self.integration_data = IntegrationData(
            integration_gateway=_MixedCapGateway(),
            integration=self.integration,
        )

    def _attribute_names_for(self, capability):
        edit_context = IntegrationAttributeItemEditContext(
            integration_data=self.integration_data,
            capability=capability,
        )
        return sorted(
            attr.integration_key.integration_name
            for attr in edit_context._capability_filtered_attribute_queryset()
        )

    def test_connect_context_excludes_import_only(self):
        self.assertEqual(
            self._attribute_names_for(IntegrationCapability.CONNECT),
            ['connect_field', 'shared_field'],
        )

    def test_import_context_excludes_connect_only(self):
        self.assertEqual(
            self._attribute_names_for(IntegrationCapability.IMPORT),
            ['import_field', 'shared_field'],
        )
