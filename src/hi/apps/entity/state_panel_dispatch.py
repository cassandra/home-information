import logging
from dataclasses import dataclass, field
from typing import List, Set

from django.template import Template
from django.template.exceptions import TemplateDoesNotExist
from django.template.loader import get_template

from hi.apps.entity.enums import DisplayContext, EntityStateRole, EntityType
from hi.apps.entity.state_panel_base import EntityStatusPanel
from hi.apps.entity.state_panel_registry import EntityStatusPanelRegistry


logger = logging.getLogger( __name__ )


@dataclass
class PanelResolution:
    panel  : EntityStatusPanel
    extras : Set[ EntityStateRole ] = field( default_factory = set )
    trace  : List[ str ]            = field( default_factory = list )


def resolve_panel(
        entity_type      : EntityType,
        display_context  : DisplayContext,
        present_roles    : Set[ EntityStateRole ],
) -> PanelResolution:
    """Choose the panel for ``(entity_type, display_context, present_roles)``.
    Type-specific panels win over fallback panels; among either group,
    lower ``priority`` wins, with ``name`` as the alphabetical tiebreaker.
    Raises ``RuntimeError`` if no fallback panel covers the context."""

    all_panels = EntityStatusPanelRegistry().all_panels()
    trace : List[ str ] = [
        f'entity_type={entity_type.name} '
        f'display_context={display_context.name} '
        f'present_roles=[{",".join(sorted(r.name for r in present_roles))}]',
    ]

    typed = sorted(
        (
            p for p in all_panels
            if p.entity_type == entity_type
            and display_context in p.display_contexts
            and p.required_roles.issubset( present_roles )
        ),
        key = lambda p: ( p.priority, p.name ),
    )
    if typed:
        chosen = typed[0]
        trace.append(
            'typed candidates: '
            + ', '.join( f'{p.name}#{p.priority}' for p in typed )
            + f' -> {chosen.name}'
        )
        return _build_resolution( chosen, present_roles, trace )

    fallbacks = sorted(
        (
            p for p in all_panels
            if p.entity_type is None
            and display_context in p.display_contexts
        ),
        key = lambda p: ( p.priority, p.name ),
    )
    if not fallbacks:
        trace.append( f'no fallback registered for {display_context.name}' )
        raise RuntimeError(
            f'No fallback panel registered for display_context={display_context.name}'
        )
    chosen = fallbacks[0]
    trace.append(
        'fallback candidates: '
        + ', '.join( f'{p.name}#{p.priority}' for p in fallbacks )
        + f' -> {chosen.name}'
    )
    return _build_resolution( chosen, present_roles, trace )


def _build_resolution( panel, present_roles, trace ):
    extras = present_roles - ( panel.required_roles | panel.optional_roles )
    if extras:
        trace.append( 'extras: ' + ','.join( sorted( r.name for r in extras ) ) )
    resolution = PanelResolution( panel = panel, extras = extras, trace = trace )
    logger.debug( 'Panel resolution:\n  ' + '\n  '.join( trace ) )
    return resolution


# Legacy template-path resolver. Kept while the render_entity_status_panel
# template tag remains; removed in Phase 3b.

SUPPORTED_DISPLAY_CONTEXTS = ( 'modal', 'list', 'grid' )

FRAMEWORK_FALLBACK_TEMPLATES = {
    'modal': 'entity/state_panels/fallback/modal.html',
    'list': 'entity/state_panels/fallback/list.html',
    'grid': 'entity/state_panels/fallback/grid.html',
}


def resolve_panel_template(
        entity_type           : EntityType,
        display_context_name  : str,
) -> Template:
    if display_context_name not in SUPPORTED_DISPLAY_CONTEXTS:
        raise ValueError(
            f'Unsupported display context: {display_context_name!r}. '
            f'Expected one of {SUPPORTED_DISPLAY_CONTEXTS}.'
        )
    type_lower = entity_type.name.lower()
    for candidate in _legacy_candidate_paths( type_lower, display_context_name ):
        try:
            return get_template( candidate )
        except TemplateDoesNotExist:
            continue
        continue
    raise TemplateDoesNotExist(
        f'No panel template found for entity_type={entity_type.name} '
        f'context={display_context_name}; framework fallback at '
        f'{FRAMEWORK_FALLBACK_TEMPLATES[display_context_name]} is missing.'
    )


def _legacy_candidate_paths( type_lower : str, display_context_name : str ) -> List[ str ]:
    return [
        f'entity/state_panels/{type_lower}/{display_context_name}.html',
        f'entity/state_panels/{type_lower}/modal.html',
        FRAMEWORK_FALLBACK_TEMPLATES[ display_context_name ],
    ]
