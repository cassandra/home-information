"""Template-path resolution for EntityStatusPanel rendering.

A panel is a self-contained bundle of templates, CSS, and (optionally)
JS that defines how an entity of a particular EntityType is rendered
in one of three display contexts: the EntityStatusView modal body, the
collection list card, and the collection grid card.

``modal.html`` is the panel's required default template. ``list.html``
and ``grid.html`` are optional per-context overrides. The framework
provides fallback templates for any entity type that has no panel."""

from typing import List

from django.template import Template
from django.template.exceptions import TemplateDoesNotExist
from django.template.loader import get_template

from hi.apps.entity.enums import EntityType


SUPPORTED_DISPLAY_CONTEXTS = ( 'modal', 'list', 'grid' )

# Per-context framework fallback used when the entity's type has no
# panel directory. All three are framework-provided and guaranteed
# to exist.
FRAMEWORK_FALLBACK_TEMPLATES = {
    'modal': 'entity/state_panels/fallback/modal.html',
    'list': 'entity/state_panels/fallback/list.html',
    'grid': 'entity/state_panels/fallback/grid.html',
}


def resolve_panel_template(
        entity_type           : EntityType,
        display_context_name  : str,
) -> Template:
    """Return the first existing template for the (entity_type,
    display_context) pair along the three-step resolution chain:

    1. Panel's context-specific template (``<type>/<context>.html``).
    2. Panel's required default template (``<type>/modal.html``).
    3. Framework fallback for the context (always exists)."""

    if display_context_name not in SUPPORTED_DISPLAY_CONTEXTS:
        raise ValueError(
            f'Unsupported display context: {display_context_name!r}. '
            f'Expected one of {SUPPORTED_DISPLAY_CONTEXTS}.'
        )

    type_lower = entity_type.name.lower()
    for candidate in _candidate_paths( type_lower, display_context_name ):
        try:
            return get_template( candidate )
        except TemplateDoesNotExist:
            continue

    raise TemplateDoesNotExist(
        f'No panel template found for entity_type={entity_type.name} '
        f'context={display_context_name}; framework fallback at '
        f'{FRAMEWORK_FALLBACK_TEMPLATES[display_context_name]} is missing.'
    )


def _candidate_paths( type_lower : str, display_context_name : str ) -> List[ str ]:
    return [
        f'entity/state_panels/{type_lower}/{display_context_name}.html',
        f'entity/state_panels/{type_lower}/modal.html',
        FRAMEWORK_FALLBACK_TEMPLATES[ display_context_name ],
    ]
