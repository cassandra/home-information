from hi.integrations.enums import IntegrationCapability
from hi.integrations.transient_models import IntegrationMetaData

from .enums import ImAttributeType


ImmichMetaData = IntegrationMetaData(
    integration_id = 'immich',
    label = 'Immich',
    attribute_type = ImAttributeType,
    allow_entity_deletion = False,
    allow_internal_attributes = False,
    logo_static_path = 'img/integrations/immich.png',
    capabilities = frozenset({
        IntegrationCapability.ATTRIBUTE_REFERENCE,
    }),
)
