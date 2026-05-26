"""
HomeBox-specific placement grouping for the integration placement modal.

HomeBox items carry up to three plausible grouping dimensions:
upstream Location, batch-popular Tag, and the heuristic EntityType
stamped by ``HbConverter.hb_item_to_entity_type``. None is reliably
best on its own — a small batch may have uniform locations, an
import from a flat HomeBox install may have no tags, and a typed
batch may not need the type breakout. The grouper picks among them
with an ordered viability fallback:

1. Group by ``integration_payload['location']``.
2. Group by each item's globally-most-popular tag.
3. Fall back to the framework's by-EntityType default.

Viability for #1 and #2 comes from
``hi.integrations.placement_stats.compute_grouping_stats``. The
EntityType fallback is used unconditionally so a tiny or uniform
batch still gets a sensible heading rather than collapsing to
ungrouped.
"""

from collections import Counter
import logging
from typing import Callable, Dict, List, Optional

from hi.apps.entity.entity_placement import (
    EntityPlacementGroup,
    EntityPlacementInput,
    EntityPlacementItem,
)
from hi.apps.entity.models import Entity

from hi.integrations.placement_stats import compute_grouping_stats


logger = logging.getLogger(__name__)


LOCATION_HEADING        = 'HomeBox Location'
LOCATION_FALLBACK_LABEL = 'Other'
TAG_HEADING             = 'HomeBox Tag'
TAG_FALLBACK_LABEL      = 'Untagged'
TYPE_HEADING            = 'Item Type'


LabelFn = Callable[[Entity], Optional[str]]


class HbPlacementGrouper:
    """Builds an ``EntityPlacementInput`` for a HomeBox import batch.

    Self-contained — does not delegate to the gateway base class.
    The by-EntityType final fallback is implemented inline against
    the same internal bucketing helper used by the Location and
    Tag passes, so HomeBox's grouping policy stays stable even if
    the framework default changes.
    """

    def __init__(
            self,
            placement_item_key_fn : Callable[[Entity], str],
    ):
        self._placement_item_key_fn = placement_item_key_fn
        return

    def group_entities(
            self, entities: List[Entity],
    ) -> EntityPlacementInput:
        """Ordered-fallback grouping: Location → primary Tag →
        EntityType. First viable wins; EntityType is used
        unconditionally as the final fallback."""
        if not entities:
            return EntityPlacementInput()

        by_location = self._group_by_location( entities = entities )
        if compute_grouping_stats( by_location ).is_viable():
            return by_location

        by_tag = self._group_by_primary_tag( entities = entities )
        if compute_grouping_stats( by_tag ).is_viable():
            return by_tag

        return self._group_by_entity_type( entities = entities )

    def _group_by_location(
            self, entities: List[Entity],
    ) -> EntityPlacementInput:
        return self._build_grouped_input(
            entities       = entities,
            label_fn       = lambda e: (e.integration_payload or {}).get( 'location' ),
            heading        = LOCATION_HEADING,
            fallback_label = LOCATION_FALLBACK_LABEL,
        )

    def _group_by_primary_tag(
            self, entities: List[Entity],
    ) -> EntityPlacementInput:
        primary_tag_lookup = self._compute_primary_tag_lookup(
            entities = entities,
        )
        return self._build_grouped_input(
            entities       = entities,
            label_fn       = lambda e: primary_tag_lookup.get( e.id ),
            heading        = TAG_HEADING,
            fallback_label = TAG_FALLBACK_LABEL,
        )

    def _group_by_entity_type(
            self, entities: List[Entity],
    ) -> EntityPlacementInput:
        # ``entity_type.label`` is never None, so the fallback
        # group never materializes; the empty label is a never-
        # used sentinel rather than a meaningful UI string.
        return self._build_grouped_input(
            entities       = entities,
            label_fn       = lambda e: e.entity_type.label,
            heading        = TYPE_HEADING,
            fallback_label = '',
        )

    @staticmethod
    def _compute_primary_tag_lookup(
            entities: List[Entity],
    ) -> Dict[int, str]:
        """For each entity, return its primary tag — the tag (from
        its own ``integration_payload['tags']`` list) with the
        highest population across the whole batch. Entities with no
        tags are absent from the returned dict.

        Biasing toward globally-popular tags (over per-item detail
        tags) is what makes the tag dimension produce a small
        number of meaningful buckets rather than one bucket per
        long-tail tag."""
        global_counts: Counter = Counter()
        for entity in entities:
            tags = (entity.integration_payload or {}).get( 'tags' ) or []
            for tag in tags:
                if tag:
                    global_counts[ tag ] += 1

        primary_tag_by_entity: Dict[int, str] = {}
        for entity in entities:
            tags = (entity.integration_payload or {}).get( 'tags' ) or []
            candidates = [ tag for tag in tags if tag ]
            if not candidates:
                continue
            # (count, name) tiebreaker keeps tied tags deterministic.
            primary_tag_by_entity[ entity.id ] = max(
                candidates,
                key = lambda tag: ( global_counts[ tag ], tag ),
            )
        return primary_tag_by_entity

    def _build_grouped_input(
            self,
            entities       : List[Entity],
            label_fn       : LabelFn,
            heading        : str,
            fallback_label : str,
    ) -> EntityPlacementInput:
        """Bucket items by ``label_fn``; items with a None label
        land in a labeled fallback group appended last. Named
        groups are sorted alphabetically for stable presentation."""
        label_to_items: Dict[str, List[EntityPlacementItem]] = {}
        fallback_items: List[EntityPlacementItem] = []
        for entity in entities:
            item = EntityPlacementItem(
                key    = self._placement_item_key_fn( entity ),
                label  = entity.name,
                entity = entity,
            )
            label = label_fn( entity )
            if label is None:
                fallback_items.append( item )
                continue
            label_to_items.setdefault( label, [] ).append( item )

        groups = [
            EntityPlacementGroup( label = label, items = label_to_items[ label ] )
            for label in sorted( label_to_items.keys() )
        ]
        if fallback_items:
            groups.append(
                EntityPlacementGroup(
                    label = fallback_label,
                    items = fallback_items,
                )
            )
        return EntityPlacementInput( groups = groups, heading = heading )
