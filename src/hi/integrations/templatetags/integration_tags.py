import logging
from django import template

from hi.integrations.models import IntegrationDetailsModel
from hi.integrations.integration_manager import IntegrationManager

logger = logging.getLogger(__name__)

register = template.Library()


@register.simple_tag
def integration_display_name( model : IntegrationDetailsModel ) -> str:
    if not model:
        return None
    integration_manager = IntegrationManager()
    gateway = integration_manager.get_integration_gateway( model.integration_id )
    metadata = gateway.get_metadata()
    return metadata.label
