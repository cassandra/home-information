import logging
from django import template

from hi.integrations.models import IntegrationDetailsModel
from hi.integrations.integration_manager import IntegrationManager

logger = logging.getLogger(__name__)

register = template.Library()


def _resolve_metadata_for_id( integration_id : str ):
    if not integration_id:
        return None
    integration_manager = IntegrationManager()
    try:
        gateway = integration_manager.get_integration_gateway( integration_id )
        return gateway.get_metadata()
    except Exception:
        pass
    return None


def _get_integration_metadata( model : IntegrationDetailsModel ):
    if not model:
        return None
    return _resolve_metadata_for_id( model.integration_id )


def _get_previous_integration_metadata( model : IntegrationDetailsModel ):
    if not model:
        return None
    return _resolve_metadata_for_id( model.previous_integration_id )


@register.simple_tag
def integration_display_name( model : IntegrationDetailsModel ) -> str:
    metadata = _get_integration_metadata( model )
    return metadata.label if metadata else None


@register.simple_tag
def integration_logo_path( model : IntegrationDetailsModel ) -> str:
    metadata = _get_integration_metadata( model )
    return metadata.logo_static_path if metadata else ''


@register.simple_tag
def previous_integration_display_name( model : IntegrationDetailsModel ) -> str:
    """The label of the integration this entity was previously
    attached to (i.e., the source of the "Detached from ..." badge).
    Returns None when the entity is not detached, or when the prior
    integration has since been removed from the system."""
    metadata = _get_previous_integration_metadata( model )
    return metadata.label if metadata else None


@register.simple_tag
def previous_integration_logo_path( model : IntegrationDetailsModel ) -> str:
    """Logo for the integration the entity was previously attached
    to. Used in the entity-detail UI to show the "Detached from ..."
    badge alongside the same logo the integration uses when active."""
    metadata = _get_previous_integration_metadata( model )
    return metadata.logo_static_path if metadata else ''

