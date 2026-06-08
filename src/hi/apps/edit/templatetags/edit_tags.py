from django import template

from hi.apps.entity.models import Entity

from hi.apps.edit.entity_membership import EntityViewMembership

register = template.Library()


@register.simple_tag( takes_context = True )
def active_entity_membership( context, entity : Entity ):
    """Resolve the add/remove-from-view control descriptor for ``entity``
    in the request's active view/collection, or None when the active view
    has no membership concept.
    """
    request = context.get( 'request' )
    if request is None:
        return None
    membership = EntityViewMembership.for_request( request )
    if membership is None:
        return None
    return {
        'is_member': membership.is_member( entity ),
        'toggle_url': membership.toggle_url( entity ),
        'target_label': membership.target_label,
    }
