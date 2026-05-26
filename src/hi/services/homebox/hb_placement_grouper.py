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
3. Fall back to the framework's by-EntityGroupType default.

Viability for #1 and #2 comes from
``hi.integrations.placement_stats.compute_grouping_stats``. The
EntityType fallback is used unconditionally so a tiny or uniform
batch still gets a sensible heading rather than collapsing to
ungrouped.

The bucketing machinery lives in
``hi.apps.entity.entity_placement.PlacementInputBuilder``; this
module just picks dimensions and labels.
"""

from collections import Counter
import logging
from typing import Callable, Dict, List

from hi.apps.entity.entity_placement import (
    EntityPlacementInput,
    PlacementInputBuilder,
)
from hi.apps.entity.models import Entity

from hi.integrations.placement_stats import compute_grouping_stats


logger = logging.getLogger(__name__)


LOCATION_HEADING        = 'HomeBox Location'
LOCATION_FALLBACK_LABEL = 'Other'
TAG_HEADING             = 'HomeBox Tag'
TAG_FALLBACK_LABEL      = 'Untagged'


class HbPlacementGrouper:
    """Builds an ``EntityPlacementInput`` for a HomeBox import batch
    via ordered viability fallback across Location, Tag, and the
    framework default by-EntityGroupType pass."""

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
        EntityGroupType. First viable wins; the by-group default is
        used unconditionally as the final fallback."""
        if not entities:
            return EntityPlacementInput()

        by_location = self._group_by_location( entities = entities )
        if compute_grouping_stats( by_location ).is_viable():
            return by_location

        by_tag = self._group_by_primary_tag( entities = entities )
        if compute_grouping_stats( by_tag ).is_viable():
            return by_tag

        return PlacementInputBuilder.by_entity_type_group(
            entities    = entities,
            item_key_fn = self._placement_item_key_fn,
        )

    def _group_by_location(
            self, entities: List[Entity],
    ) -> EntityPlacementInput:
        return PlacementInputBuilder.by_label_fn(
            entities       = entities,
            item_key_fn    = self._placement_item_key_fn,
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
        return PlacementInputBuilder.by_label_fn(
            entities       = entities,
            item_key_fn    = self._placement_item_key_fn,
            label_fn       = lambda e: primary_tag_lookup.get( e.id ),
            heading        = TAG_HEADING,
            fallback_label = TAG_FALLBACK_LABEL,
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
