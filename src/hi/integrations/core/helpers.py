from django.db import transaction

from hi.apps.attribute.enums import AttributeType

from hi.integrations.core.integration_key import IntegrationKey
from hi.integrations.core.models import Integration, IntegrationAttribute
from hi.integrations.core.transient_models import IntegrationMetaData


class IntegrationHelperMixin:

    def get_or_create_integration( self, integration_metadata : IntegrationMetaData ):
        try:
            return Integration.objects.get(
                integration_id = integration_metadata.integration_id,
            )
        except Integration.DoesNotExist:
            pass

        with transaction.atomic():
            integration = Integration.objects.create(
                integration_id = integration_metadata.integration_id,
                is_enabled = False,
            )
            IntegrationAttributeType = integration_metadata.attribute_type
            for attribute_type in IntegrationAttributeType:
                integration_key = IntegrationKey(
                    integration_id = integration.integration_id,
                    integration_name = str(attribute_type),
                )
                IntegrationAttribute.objects.create(
                    integration = integration,
                    name = attribute_type.label,
                    value = '',
                    value_type_str = str(attribute_type.value_type),
                    integration_key = integration_key,
                    attribute_type_str = AttributeType.PREDEFINED,
                    is_editable = attribute_type.is_editable,
                    is_required = attribute_type.is_required,
                )
                continue
        return integration
    
