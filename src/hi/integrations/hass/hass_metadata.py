from hi.integrations.core.transient_models import IntegrationMetaData

from .enums import HassAttributeType


HassMetaData = IntegrationMetaData(
    integration_id = 'hass',
    manage_url_name = 'hass_manage',
    label = 'Home Assistant',
    attribute_type = HassAttributeType,
    allow_entity_deletion = False,
)
