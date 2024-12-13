from hi.integrations.transient_models import IntegrationMetaData

from .enums import HassAttributeType


HassMetaData = IntegrationMetaData(
    integration_id = 'hass',
    label = 'Home Assistant',
    attribute_type = HassAttributeType,
    allow_entity_deletion = False,
)
