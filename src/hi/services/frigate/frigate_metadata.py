from hi.integrations.transient_models import IntegrationMetaData

from .enums import FrigateAttributeType


FrigateMetaData = IntegrationMetaData(
    integration_id = 'frigate',
    label = 'Frigate',
    attribute_type = FrigateAttributeType,
    allow_entity_deletion = False,
    logo_static_path = 'img/integrations/frigate.png',
)
