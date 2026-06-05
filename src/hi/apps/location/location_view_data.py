from dataclasses import dataclass
from typing import Dict, Generator, List, Set

from hi.apps.collection.models import Collection, CollectionPath, CollectionPosition
from hi.apps.common.svg_models import SvgIconItem, SvgPathItem
from hi.apps.entity.entity_state_role_order import ENTITY_PRIMARY_STATE_ORDERING
from hi.apps.entity.models import Entity, EntityPosition, EntityPath
from hi.apps.location.svg_item_factory import SvgItemFactory
from hi.apps.monitor.display_data import EntityStateDisplayData
from hi.apps.monitor.status_data import EntityStateStatusData

from .models import LocationView


@dataclass
class LocationViewData:
    """
    Encapsulates all the data needed to render overlaying a Location's SVG
    for a given LocationView.
    """
    location_view                            : LocationView
    entity_positions                         : List[ EntityPosition ]
    entity_paths                             : List[ EntityPath ]
    collection_positions                     : List[ CollectionPosition ]
    collection_paths                         : List[ CollectionPath ]
    unpositioned_collections                 : List[ Collection ]
    orphan_entities                          : Set[ Entity ]
    entity_to_entity_state_status_data_list  : Dict[ Entity, List[ EntityStateStatusData ]]
    
    def __post_init__(self):
        self._svg_item_factory = SvgItemFactory()
        # Primary-state map is computed first; the state-id map is
        # derived from it so the entity's ``<g>`` element carries
        # exactly one ``data-state-id`` (the primary state). That
        # gives the polling dispatcher a single anchor for SVG
        # styling updates on this entity's icon.
        self._latest_entity_state_status_data_map = self._get_latest_entity_state_status_data_map()
        self._state_id_map = self._get_state_id_map()
        return

    def svg_icon_items(self) -> Generator[ SvgIconItem, None, None ]:

        for entity_position in self.entity_positions:

            state_id = self._state_id_map.get( entity_position.entity )
            latest_entity_state_status_data = self._latest_entity_state_status_data_map.get(
                entity_position.entity,
            )
            if latest_entity_state_status_data:
                status_display_data = EntityStateDisplayData(
                    entity_state_status_data = latest_entity_state_status_data,
                )
                svg_status_style = status_display_data.svg_status_style
            else:
                svg_status_style = None

            svg_icon_item = self._svg_item_factory.create_svg_icon_item(
                item = entity_position.entity,
                position = entity_position,
                state_id = state_id,
                svg_status_style = svg_status_style,
            )
            yield svg_icon_item
            continue

        for collection_position in self.collection_positions:
            svg_icon_item = self._svg_item_factory.create_svg_icon_item(
                item = collection_position.collection,
                position = collection_position,
            )
            yield svg_icon_item
            continue
        return

    def svg_path_items(self) -> Generator[ SvgPathItem, None, None ]:

        for entity_path in self.entity_paths:

            state_id = self._state_id_map.get( entity_path.entity )
            latest_entity_state_status_data = self._latest_entity_state_status_data_map.get(
                entity_path.entity,
            )
            if latest_entity_state_status_data:
                status_display_data = EntityStateDisplayData(
                    entity_state_status_data = latest_entity_state_status_data,
                )
                svg_status_style = status_display_data.svg_status_style
            else:
                svg_status_style = None

            svg_path_item = self._svg_item_factory.create_svg_path_item(
                item = entity_path.entity,
                path = entity_path,
                state_id = state_id,
                svg_status_style = svg_status_style,
            )
            yield svg_path_item
            continue

        for collection_path in self.collection_paths:
            svg_path_item = self._svg_item_factory.create_svg_path_item(
                item = collection_path.collection,
                path = collection_path,
            )
            yield svg_path_item
            continue
        return

    def _get_state_id_map(self):
        # One state id per entity — the primary state's id — so the SVG
        # icon/path elements carry ``data-state-id`` and the polling
        # dispatcher can target them. Entities with a current response keep
        # their responded primary (so the marker and the rendered status
        # value reference the same state); entities with states but no current
        # response fall back to their configured primary, rendered with the
        # existing empty/unknown status, so a later state change is picked up
        # live by polling instead of being stuck until a full re-render.
        state_id_map = dict()
        for entity, status_data_list in self.entity_to_entity_state_status_data_list.items():
            responded = self._latest_entity_state_status_data_map.get( entity )
            if responded is not None:
                state_id_map[entity] = responded.entity_state.id
                continue
            primary = self._pick_primary_status_data( entity, status_data_list )
            if primary is not None:
                state_id_map[entity] = primary.entity_state.id
            continue
        return state_id_map

    def _get_latest_entity_state_status_data_map(self):
        # Per-entity primary-state selection: among states with a
        # sensor response, pick the one whose role ranks highest in
        # ``ENTITY_PRIMARY_STATE_ORDERING`` for the entity's
        # EntityType. The picked state's value drives the entity's
        # rendered ``status`` attribute (and from there, the CSS-bound
        # visual styling). Multi-sensor correctness is inherited: each
        # EntityStateStatusData.latest_sensor_response already reflects
        # the time-latest response across all of that state's sensors.
        latest_entity_state_status_data_map = dict()
        for entity, entity_state_status_data_list in self.entity_to_entity_state_status_data_list.items():
            with_responses_list = [ x for x in entity_state_status_data_list if x.latest_sensor_response ]
            primary = self._pick_primary_status_data( entity, with_responses_list )
            if primary is not None:
                latest_entity_state_status_data_map[entity] = primary
            continue
        return latest_entity_state_status_data_map

    def _pick_primary_status_data(self, entity, status_data_list):
        # Single source of the primary-state selection: from a list of the
        # entity's EntityStateStatusData, pick the one whose state role ranks
        # highest in ``ENTITY_PRIMARY_STATE_ORDERING`` for the entity's type.
        # Callers choose the candidate set (response-only vs. all states); this
        # owns the ordering. Returns None for an empty list.
        if not status_data_list:
            return None
        return min(
            status_data_list,
            key = lambda d: ENTITY_PRIMARY_STATE_ORDERING.sort_key(
                d.entity_state.entity_state_role, entity.entity_type,
            ),
        )
