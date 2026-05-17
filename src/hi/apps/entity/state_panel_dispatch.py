import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Set, TYPE_CHECKING

from hi.apps.entity.enums import DisplayContext, EntityStateRole, EntityType
from hi.apps.entity.state_panel_base import EntityStatePanel
from hi.apps.entity.state_panel_registry import EntityStatePanelRegistry

if TYPE_CHECKING:
    from hi.apps.monitor.display_data import EntityDisplayData


logger = logging.getLogger( __name__ )


@dataclass
class PanelResolution:
    panel  : EntityStatePanel
    extras : Set[ EntityStateRole ] = field( default_factory = set )
    trace  : List[ str ]            = field( default_factory = list )


@dataclass
class EntityStatePanelData:
    """An entity prepared for rendering through the panel framework in a
    specific display context. Produced by
    ``StatePanelDispatcher.build_state_panel_data``; consumed identically
    by both the entity status modal and the collection card wrappers."""

    entity_status_data : 'EntityDisplayData'
    panel_template     : str
    panel_context      : Dict[ str, Any ]
    trace              : List[ str ]            = field( default_factory = list )

    @property
    def entity(self):
        return self.entity_status_data.entity

    @property
    def display_category(self):
        return self.entity_status_data.display_category

    @property
    def display_only_svg_icon_item(self):
        return self.entity_status_data.display_only_svg_icon_item

    @property
    def extras_state_data_list(self):
        return self.panel_context[ 'extras_state_data_list' ]


class StatePanelDispatcher:

    @classmethod
    def build_state_panel_data(
            cls,
            entity_display_data,
            display_context : DisplayContext,
    ) -> EntityStatePanelData:
        resolution = cls.resolve_panel_for( entity_display_data, display_context )
        panel_context = cls.build_panel_context( entity_display_data, resolution )
        return EntityStatePanelData(
            entity_status_data = entity_display_data,
            panel_template     = resolution.panel.template_name,
            panel_context      = panel_context,
            trace              = resolution.trace,
        )

    @classmethod
    def resolve_panel_for(
            cls,
            entity_display_data,
            display_context : DisplayContext,
    ) -> PanelResolution:
        return cls.resolve_panel(
            entity_type     = entity_display_data.entity.entity_type,
            display_context = display_context,
            present_roles   = entity_display_data.present_roles,
        )

    @classmethod
    def resolve_panel(
            cls,
            entity_type      : EntityType,
            display_context  : DisplayContext,
            present_roles    : Set[ EntityStateRole ],
    ) -> PanelResolution:
        """Choose the panel for ``(entity_type, display_context, present_roles)``.
        Type-specific panels win over fallback panels; among either group,
        lower ``priority`` wins, with ``name`` as the alphabetical tiebreaker.
        Raises ``RuntimeError`` if no fallback panel covers the context."""

        all_panels = EntityStatePanelRegistry().all_panels()
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
            return cls._build_resolution( chosen, present_roles, trace )

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
        return cls._build_resolution( chosen, present_roles, trace )

    @classmethod
    def build_panel_context(
            cls,
            entity_display_data,
            resolution : PanelResolution,
    ) -> Dict[ str, Any ]:
        """Build the flat template context for ``resolution.panel.template_name``.
        ``state_status_data_list`` and ``state_status_data_by_role`` are filtered
        to the panel's declared (required + optional) roles, except for fallback
        panels (``entity_type is None``) which see every state.
        ``extras_state_data_list`` is the per-state projection of
        ``resolution.extras`` for the framework's modal extras section."""

        panel = resolution.panel
        all_state_data_list = entity_display_data.state_status_data_list

        if panel.entity_type is None:
            state_data_list = all_state_data_list
            state_data_by_role = entity_display_data.state_status_data_by_role
            extras_state_data_list = []
        else:
            declared = panel.required_roles | panel.optional_roles
            state_data_list = [
                d for d in all_state_data_list
                if d.entity_state.entity_state_role in declared
            ]
            state_data_by_role = {
                name: data
                for name, data in entity_display_data.state_status_data_by_role.items()
                if data.entity_state.entity_state_role in declared
            }
            extras_state_data_list = [
                d for d in all_state_data_list
                if d.entity_state.entity_state_role in resolution.extras
            ]

        return {
            'entity'                     : entity_display_data.entity,
            'entity_status_data'         : entity_display_data,
            'state_status_data_list'     : state_data_list,
            'state_status_data_by_role'  : state_data_by_role,
            'entity_for_video'           : entity_display_data.entity_for_video,
            'display_only_svg_icon_item' : entity_display_data.display_only_svg_icon_item,
            'display_category'           : entity_display_data.display_category,
            'extras_state_data_list'     : extras_state_data_list,
        }

    @classmethod
    def _build_resolution( cls, panel, present_roles, trace ):
        extras = present_roles - ( panel.required_roles | panel.optional_roles )
        if extras:
            trace.append( 'extras: ' + ','.join( sorted( r.name for r in extras ) ) )
        resolution = PanelResolution( panel = panel, extras = extras, trace = trace )
        logger.debug( 'Panel resolution:\n  ' + '\n  '.join( trace ) )
        return resolution
