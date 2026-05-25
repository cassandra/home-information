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
    attached to (i.e., the source of the "From ..." badge).
    Returns None when the entity carries no integration provenance,
    or when the prior integration has since been removed from the
    system."""
    metadata = _get_previous_integration_metadata( model )
    return metadata.label if metadata else None


@register.simple_tag
def previous_integration_logo_path( model : IntegrationDetailsModel ) -> str:
    """Logo for the integration the entity was previously attached
    to. Used in the entity-detail UI to show the "From ..." badge
    alongside the same logo the integration uses when active."""
    metadata = _get_previous_integration_metadata( model )
    return metadata.logo_static_path if metadata else ''


@register.inclusion_tag( 'integrations/connector/panes/integration_health_banner.html' )
def integration_health_banner( integration_id : str, context_message : str = None ):
    """Render a banner when the integration is in a non-healthy state.

    Renders nothing for HEALTHY or when the integration cannot be
    resolved. Use from any UI that depends on an integration's data
    so the operator is alerted when displayed state may be stale or
    actions may not take effect.

    Parameters:
      integration_id   : The entity's / surface's owning integration id.
      context_message  : Optional message describing how the integration's
                         degraded state affects the surrounding UI."""
    if not integration_id:
        return { 'health_status': None }
    try:
        gateway = IntegrationManager().get_integration_gateway( integration_id )
        connector = gateway.get_connector()
        if connector is None:
            return { 'health_status': None }
        provider = connector.get_health_status_provider()
        health_status = provider.health_status
        metadata = gateway.get_metadata()
    except Exception:
        logger.debug( 'integration_health_banner: lookup failed for %r',
                      integration_id )
        return { 'health_status': None }
    return {
        'health_status': health_status,
        'integration_label': metadata.label if metadata else integration_id,
        'context_message': context_message,
    }

