from django.db import transaction

from hi.apps.attribute.enums import AttributeType

from hi.integrations.core.enums import IntegrationAttributeType
from hi.integrations.core.integration_key import IntegrationKey
from hi.integrations.core.models import Integration, IntegrationAttribute
from hi.integrations.core.transient_models import IntegrationMetaData


class IntegrationHelperMixin:

    def get_or_create_integration( self, integration_metadata : IntegrationMetaData ):
        try:
            integration = Integration.objects.get(
                integration_id = integration_metadata.integration_id,
            )
            self._ensure_all_attributes_exist(
                integration_metadata = integration_metadata,
                integration = integration,
            )
            return integration
        except Integration.DoesNotExist:
            pass

        with transaction.atomic():
            integration = Integration.objects.create(
                integration_id = integration_metadata.integration_id,
                is_enabled = False,
            )
            AttributeType = integration_metadata.attribute_type
            for attribute_type in AttributeType:
                self._create_integration_attribute(
                    integration = integration,
                    attribute_type = attribute_type,
                )
                continue
        return integration
    
    def _ensure_all_attributes_exist( self,
                                      integration_metadata  : IntegrationMetaData,
                                      integration           : Integration ):
        """
        After an integration is created, we need to be able to detect if any
        new attributes might have been defined.  This allows new code
        features to be added for existing installations.
        """

        new_attribute_types = set()
        existing_attribute_integration_keys = set([ x.integration_key
                                                    for x in integration.attributes.all() ])
        
        AttributeType = integration_metadata.attribute_type
        for attribute_type in AttributeType:
            integration_key = IntegrationKey(
                integration_id = integration.integration_id,
                integration_name = str(attribute_type),
            )
            if integration_key not in existing_attribute_integration_keys:
                new_attribute_types.add( attribute_type )
            continue
        
        if new_attribute_types:
            with transaction.atomic():
                for attribute_type in new_attribute_types:
                    self._create_integration_attribute(
                        integration = integration,
                        attribute_type = attribute_type,
                    )
                    continue
        return
        
    def _create_integration_attribute( self,
                                       integration     : Integration,
                                       attribute_type  : IntegrationAttributeType ):
        integration_key = IntegrationKey(
            integration_id = integration.integration_id,
            integration_name = str(attribute_type),
        )
        IntegrationAttribute.objects.create(
            integration = integration,
            name = attribute_type.label,
            value = attribute_type.value_type.initial_value,
            value_type_str = str(attribute_type.value_type),
            integration_key_str = str(integration_key),
            attribute_type_str = AttributeType.PREDEFINED,
            is_editable = attribute_type.is_editable,
            is_required = attribute_type.is_required,
        )
        return
                
