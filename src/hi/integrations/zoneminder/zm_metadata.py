from hi.integrations.core.transient_models import IntegrationMetaData

from .enums import ZmAttributeType


ZmMetaData = IntegrationMetaData(
    integration_id = 'zm',
    label = 'ZoneMinder',
    attribute_type = ZmAttributeType,
    allow_entity_deletion = False,
)
