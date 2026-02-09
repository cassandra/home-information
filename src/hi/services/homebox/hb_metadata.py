from hi.integrations.transient_models import IntegrationMetaData

from .enums import HbAttributeType


HbMetaData = IntegrationMetaData(
    integration_id = 'hb',
    label = 'HomeBox',
    attribute_type = HbAttributeType,
    allow_entity_deletion = False,
)
