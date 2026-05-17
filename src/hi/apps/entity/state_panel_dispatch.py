import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Set

from hi.apps.entity.enums import DisplayContext, EntityStateRole, EntityType
from hi.apps.entity.state_panel_base import EntityStatePanel
from hi.apps.entity.state_panel_registry import EntityStatePanelRegistry
from hi.apps.monitor.display_data import EntityDisplayData, EntityStateDisplayData


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
    by both the entity status modal and the collection card wrappers.

    ``panel_context`` carries the panel-template variables (filtered to
    declared roles for typed panels, unfiltered for fallback panels).
    ``extras_state_data_list`` is the framework-managed projection of
    roles outside the panel's declared set; the modal extras section
    renders it."""

    entity_display_data    : EntityDisplayData
    panel_template         : str
    panel_context          : Dict[ str, Any ]
    extras_state_data_list : List[ EntityStateDisplayData ] = field( default_factory = list )
    trace                  : List[ str ]                    = field( default_factory = list )

    # Forwarded for template ergonomics — templates read
    # ``state_panel_data.entity`` etc. without descending through
    # ``entity_display_data``.
    @property
    def entity(self):
        return self.entity_display_data.entity

    @property
    def display_category(self):
        return self.entity_display_data.display_category

    @property
    def display_only_svg_icon_item(self):
        return self.entity_display_data.display_only_svg_icon_item

    @property
    def entity_for_video(self):
        return self.entity_display_data.entity_for_video


class StatePanelDispatcher:

    @classmethod
    def build_state_panel_data(
            cls,
            entity_display_data : EntityDisplayData,
            display_context     : DisplayContext,
            debug               : bool = False,
    ) -> EntityStatePanelData:
        resolution = cls.resolve_panel_for(
            entity_display_data, display_context, debug = debug,
        )
        panel = resolution.panel

        if panel.entity_type is None:
            # Fallback panels see every state; nothing is "extras."
            state_list = entity_display_data.state_status_data_list
            by_role = entity_display_data.state_status_data_by_role
            extras_list : List[ EntityStateDisplayData ] = []
        else:
            declared = panel.required_roles | panel.optional_roles
            state_list, by_role = entity_display_data.filter_to_roles( declared )
            extras_list = [
                d for d in entity_display_data.state_status_data_list
                if d.entity_state.entity_state_role in resolution.extras
            ]

        panel_context : Dict[ str, Any ] = {
            'entity'                     : entity_display_data.entity,
            'entity_status_data'         : entity_display_data,
            'state_status_data_list'     : state_list,
            'state_status_data_by_role'  : by_role,
            'entity_for_video'           : entity_display_data.entity_for_video,
            'display_only_svg_icon_item' : entity_display_data.display_only_svg_icon_item,
            'display_category'           : entity_display_data.display_category,
        }
        return EntityStatePanelData(
            entity_display_data    = entity_display_data,
            panel_template         = panel.template_name,
            panel_context          = panel_context,
            extras_state_data_list = extras_list,
            trace                  = resolution.trace,
        )

    @classmethod
    def resolve_panel_for(
            cls,
            entity_display_data : EntityDisplayData,
            display_context     : DisplayContext,
            debug               : bool = False,
    ) -> PanelResolution:
        return cls.resolve_panel(
            entity_type     = entity_display_data.entity.entity_type,
            display_context = display_context,
            present_roles   = entity_display_data.present_roles,
            debug           = debug,
        )

    @classmethod
    def resolve_panel(
            cls,
            entity_type     : EntityType,
            display_context : DisplayContext,
            present_roles   : Set[ EntityStateRole ],
            debug           : bool = False,
    ) -> PanelResolution:
        """Choose the panel for ``(entity_type, display_context, present_roles)``.
        Type-specific panels win over fallback panels; among either group,
        lower ``priority`` wins, with ``name`` as the alphabetical tiebreaker.
        Raises ``RuntimeError`` if no fallback panel covers the context.

        The trace is only built when ``debug`` is True or DEBUG-level
        logging is enabled — the production hot path (one dispatch per
        collection card) skips the trace string formatting entirely."""

        want_trace = debug or logger.isEnabledFor( logging.DEBUG )
        all_panels = EntityStatePanelRegistry().all_panels()
        trace : List[ str ] = []
        if want_trace:
            trace.append(
                f'entity_type={entity_type.name} '
                f'display_context={display_context.name} '
                f'present_roles=[{",".join(sorted(r.name for r in present_roles))}]'
            )

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
            chosen = typed[ 0 ]
            if want_trace:
                trace.append(
                    'typed candidates: '
                    + ', '.join( f'{p.name}#{p.priority}' for p in typed )
                    + f' -> {chosen.name}'
                )
            return cls._build_resolution( chosen, present_roles, trace, want_trace )

        fallbacks = sorted(
            (
                p for p in all_panels
                if p.entity_type is None
                and display_context in p.display_contexts
            ),
            key = lambda p: ( p.priority, p.name ),
        )
        if not fallbacks:
            if want_trace:
                trace.append( f'no fallback registered for {display_context.name}' )
            raise RuntimeError(
                f'No fallback panel registered for display_context={display_context.name}'
            )
        chosen = fallbacks[ 0 ]
        if want_trace:
            trace.append(
                'fallback candidates: '
                + ', '.join( f'{p.name}#{p.priority}' for p in fallbacks )
                + f' -> {chosen.name}'
            )
        return cls._build_resolution( chosen, present_roles, trace, want_trace )

    @classmethod
    def _build_resolution( cls, panel, present_roles, trace, want_trace ):
        extras = present_roles - ( panel.required_roles | panel.optional_roles )
        if want_trace and extras:
            trace.append( 'extras: ' + ','.join( sorted( r.name for r in extras ) ) )
        resolution = PanelResolution( panel = panel, extras = extras, trace = trace )
        if want_trace and trace:
            logger.debug( 'Panel resolution:\n  ' + '\n  '.join( trace ) )
        return resolution
