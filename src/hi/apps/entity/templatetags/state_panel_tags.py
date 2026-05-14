"""Template tags for the EntityStatusPanel framework.

``render_entity_status_panel`` is the dispatch point used at each
panel call site (EntityStatus modal body, collection list card,
collection grid card). It resolves a template along the panel
fallback chain and renders it with the parent context plus
panel-specific additions.

``panel_state`` is a presentation helper for panel templates that
need to pull a specific EntityState by ``EntityStateRole`` (e.g.,
the thermostat panel reaching for the current-temperature state)."""

from typing import Optional

from django import template

from hi.apps.entity.enums import EntityStateRole
from hi.apps.entity.models import Entity, EntityState
from hi.apps.entity.state_panel_dispatch import (
    SUPPORTED_DISPLAY_CONTEXTS,
    resolve_panel_template,
)


register = template.Library()


@register.simple_tag( takes_context = True )
def render_entity_status_panel( context, entity : Entity, display_context_name : str ):
    """Render the panel for ``entity`` in ``display_context_name``.

    The parent context is flattened and passed through; the panel
    template can read the same variables its call site had in scope
    (e.g., ``entity_status_data`` from the EntityStatusView modal,
    ``entity_state_status_data_list`` from collection cards)."""

    if display_context_name not in SUPPORTED_DISPLAY_CONTEXTS:
        raise ValueError(
            f'Unsupported display context: {display_context_name!r}. '
            f'Expected one of {SUPPORTED_DISPLAY_CONTEXTS}.'
        )

    template_obj = resolve_panel_template(
        entity_type = entity.entity_type,
        display_context_name = display_context_name,
    )
    flat = context.flatten()
    flat[ 'entity' ] = entity
    flat[ 'display_context_name' ] = display_context_name
    return template_obj.render( flat )


@register.simple_tag
def panel_state( entity : Entity, role : str ) -> Optional[ EntityState ]:
    """Return the EntityState on ``entity`` whose role matches
    ``role`` (case-insensitive name match against ``EntityStateRole``),
    or ``None`` when no such state exists. Walks both the entity's
    own states and delegated states."""

    try:
        role_enum = EntityStateRole.from_name( role )
    except ValueError:
        return None

    for state in entity.states.all():
        if state.entity_state_role == role_enum:
            return state
    for delegation in entity.entity_state_delegations.select_related( 'entity_state' ).all():
        if delegation.entity_state.entity_state_role == role_enum:
            return delegation.entity_state
    return None
