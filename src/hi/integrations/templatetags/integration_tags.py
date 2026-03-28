import logging
from django import template

from hi.integrations.models import IntegrationDetailsModel
from hi.integrations.integration_manager import IntegrationManager

logger = logging.getLogger(__name__)

register = template.Library()


def _get_integration_metadata( model : IntegrationDetailsModel ):
    if not model:
        return None
    integration_manager = IntegrationManager()
    try:
        gateway = integration_manager.get_integration_gateway( model.integration_id )
        return gateway.get_metadata()
    except Exception:
        pass
    return None


@register.simple_tag
def integration_display_name( model : IntegrationDetailsModel ) -> str:
    metadata = _get_integration_metadata( model )
    return metadata.label if metadata else None


@register.simple_tag
def integration_logo_path( model : IntegrationDetailsModel ) -> str:
    metadata = _get_integration_metadata( model )
    return metadata.logo_static_path if metadata else ''

