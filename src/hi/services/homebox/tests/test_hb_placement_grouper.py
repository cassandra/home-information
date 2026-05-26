"""
End-to-end coverage for ``HbPlacementGrouper``.

The grouper is the policy implementation behind
``HomeBoxGateway.group_entities_for_placement``. These tests
exercise the ordered-fallback selection against real ``Entity``
rows carrying ``integration_payload`` shapes that match what
``HbConverter.hb_item_to_entity_payload`` produces.
"""
import logging
from typing import List

from django.test import TestCase

from hi.apps.entity.enums import EntityType
from hi.apps.entity.models import Entity

from hi.services.homebox.hb_metadata import HbMetaData
from hi.services.homebox.hb_placement_grouper import (
    HbPlacementGrouper,
    LOCATION_FALLBACK_LABEL,
    LOCATION_HEADING,
    TAG_FALLBACK_LABEL,
    TAG_HEADING,
    TYPE_HEADING,
)
from hi.services.homebox.integration import HomeBoxGateway


logging.disable(logging.CRITICAL)


def _create_entity(name: str, entity_type: EntityType, payload: dict) -> Entity:
    return Entity.objects.create(
        name = name,
        entity_type_str = str(entity_type),
        integration_id = HbMetaData.integration_id,
        integration_name = f'hb-{name}',
        integration_payload = payload,
    )


def _grouper() -> HbPlacementGrouper:
    """Build a grouper wired to the gateway's item-key fn so the
    item keys in produced inputs match production output."""
    return HbPlacementGrouper(
        placement_item_key_fn = HomeBoxGateway()._placement_item_key,
    )


def _group_label_to_count(placement_input) -> dict:
    return {
        group.label: len(group.items) for group in placement_input.groups
    }


class TestHbPlacementGrouperEmpty(TestCase):

    def test_empty_returns_empty_input(self):
        result = _grouper().group_entities(entities=[])
        self.assertTrue(result.is_empty())
        # Heading falls back to the dataclass default; we don't
        # care which dimension's heading it lands on for an
        # empty batch, only that nothing renders.
        self.assertEqual(result.groups, [])
        self.assertEqual(result.ungrouped_items, [])


class TestHbPlacementGrouperLocationStrategy(TestCase):
    """Location-grouped placements are the top of the fallback
    order — confirm they win when locations are well-distributed."""

    def test_well_distributed_locations_win(self):
        entities: List[Entity] = []
        for index, location in enumerate(
                ['Garage', 'Garage', 'Garage',
                 'Office', 'Office', 'Office',
                 'Kitchen', 'Kitchen', 'Kitchen']):
            entities.append(_create_entity(
                name = f'Item {index}',
                entity_type = EntityType.OTHER,
                payload = {'location': location, 'tags': []},
            ))

        result = _grouper().group_entities(entities=entities)

        self.assertEqual(result.heading, LOCATION_HEADING)
        self.assertEqual(
            _group_label_to_count(result),
            {'Garage': 3, 'Kitchen': 3, 'Office': 3},
        )
        self.assertEqual(result.ungrouped_items, [])

    def test_unlocated_items_land_in_fallback_group(self):
        entities = [
            _create_entity('A', EntityType.OTHER, {'location': 'Garage', 'tags': []}),
            _create_entity('B', EntityType.OTHER, {'location': 'Garage', 'tags': []}),
            _create_entity('C', EntityType.OTHER, {'location': 'Garage', 'tags': []}),
            _create_entity('D', EntityType.OTHER, {'location': 'Office', 'tags': []}),
            _create_entity('E', EntityType.OTHER, {'location': 'Office', 'tags': []}),
            _create_entity('F', EntityType.OTHER, {'location': 'Office', 'tags': []}),
            _create_entity('G', EntityType.OTHER, {'location': None, 'tags': []}),
        ]

        result = _grouper().group_entities(entities=entities)

        self.assertEqual(result.heading, LOCATION_HEADING)
        counts = _group_label_to_count(result)
        self.assertEqual(counts.get('Garage'), 3)
        self.assertEqual(counts.get('Office'), 3)
        self.assertEqual(counts.get(LOCATION_FALLBACK_LABEL), 1)
        # Fallback group is appended after the alphabetically-
        # sorted named groups.
        self.assertEqual(result.groups[-1].label, LOCATION_FALLBACK_LABEL)

    def test_single_dominant_location_falls_through(self):
        # 10 of 11 items in 'Garage' → concentration ≈ 0.909,
        # over the 0.9 default ceiling, so Location is not
        # viable and the grouper falls through to another
        # dimension. (9/10 = 0.9 would sit exactly at the
        # threshold; the helper admits it.)
        entities = []
        for i in range(10):
            entities.append(_create_entity(
                f'Item {i}', EntityType.OTHER,
                {'location': 'Garage', 'tags': ['tools']},
            ))
        entities.append(_create_entity(
            'Lone', EntityType.OTHER,
            {'location': 'Office', 'tags': ['tools']},
        ))

        result = _grouper().group_entities(entities=entities)
        self.assertNotEqual(result.heading, LOCATION_HEADING)


class TestHbPlacementGrouperTagStrategy(TestCase):
    """Tag becomes the chosen dimension when Location isn't viable
    but Tag is. Verify primary-tag selection picks globally-
    popular tags over per-item detail tags."""

    def test_primary_tag_prefers_globally_popular_over_local(self):
        # Five items share the broadly-popular 'tools' tag. Three
        # of them ALSO carry a unique detail tag. Location is
        # absent everywhere so the location strategy is disqualified.
        # Expected primary-tag-grouping picks 'tools' for items that
        # have it, leaving items without 'tools' for the second group.
        entities = [
            _create_entity('A', EntityType.OTHER, {'location': None, 'tags': ['tools', 'red']}),
            _create_entity('B', EntityType.OTHER, {'location': None, 'tags': ['tools', 'blue']}),
            _create_entity('C', EntityType.OTHER, {'location': None, 'tags': ['tools', 'green']}),
            _create_entity('D', EntityType.OTHER, {'location': None, 'tags': ['tools']}),
            _create_entity('E', EntityType.OTHER, {'location': None, 'tags': ['tools']}),
            _create_entity('F', EntityType.OTHER, {'location': None, 'tags': ['kitchen']}),
            _create_entity('G', EntityType.OTHER, {'location': None, 'tags': ['kitchen']}),
            _create_entity('H', EntityType.OTHER, {'location': None, 'tags': ['kitchen']}),
        ]

        result = _grouper().group_entities(entities=entities)

        self.assertEqual(result.heading, TAG_HEADING)
        counts = _group_label_to_count(result)
        self.assertEqual(counts.get('tools'), 5)
        self.assertEqual(counts.get('kitchen'), 3)

    def test_untagged_items_land_in_fallback_group(self):
        entities = []
        for i in range(4):
            entities.append(_create_entity(
                f'T{i}', EntityType.OTHER,
                {'location': None, 'tags': ['tools']},
            ))
        for i in range(4):
            entities.append(_create_entity(
                f'K{i}', EntityType.OTHER,
                {'location': None, 'tags': ['kitchen']},
            ))
        entities.append(_create_entity(
            'X', EntityType.OTHER,
            {'location': None, 'tags': []},
        ))
        entities.append(_create_entity(
            'Y', EntityType.OTHER,
            {'location': None, 'tags': []},
        ))

        result = _grouper().group_entities(entities=entities)

        self.assertEqual(result.heading, TAG_HEADING)
        counts = _group_label_to_count(result)
        self.assertEqual(counts.get('tools'), 4)
        self.assertEqual(counts.get('kitchen'), 4)
        self.assertEqual(counts.get(TAG_FALLBACK_LABEL), 2)


class TestHbPlacementGrouperTypeFallback(TestCase):
    """EntityType is the unconditional final fallback. Verify it
    runs when neither Location nor Tag is viable AND that its
    heading is overridden from the framework default."""

    def test_falls_through_to_type_when_neither_dimension_viable(self):
        # Two items each, location/tags blank — too small and
        # too uniform for Location or Tag to be viable.
        entities = [
            _create_entity('A', EntityType.LIGHT, {'location': None, 'tags': []}),
            _create_entity('B', EntityType.LIGHT, {'location': None, 'tags': []}),
            _create_entity('C', EntityType.LIGHT, {'location': None, 'tags': []}),
            _create_entity('D', EntityType.CAMERA, {'location': None, 'tags': []}),
            _create_entity('E', EntityType.CAMERA, {'location': None, 'tags': []}),
            _create_entity('F', EntityType.CAMERA, {'location': None, 'tags': []}),
        ]

        result = _grouper().group_entities(entities=entities)

        self.assertEqual(result.heading, TYPE_HEADING)
        labels = {group.label for group in result.groups}
        self.assertIn(EntityType.LIGHT.label, labels)
        self.assertIn(EntityType.CAMERA.label, labels)


class TestHomeBoxGatewayGroupingIntegration(TestCase):
    """Smoke test the gateway override actually routes through the
    grouper so the wiring (and ``_placement_item_key`` injection)
    stays alive."""

    def test_gateway_override_uses_location_when_viable(self):
        entities = []
        for location in ['Garage', 'Garage', 'Garage',
                         'Office', 'Office', 'Office',
                         'Kitchen', 'Kitchen', 'Kitchen']:
            entities.append(_create_entity(
                f'{location}-Item-{len(entities)}',
                EntityType.OTHER,
                {'location': location, 'tags': []},
            ))

        result = HomeBoxGateway().group_entities_for_placement(entities)

        self.assertEqual(result.heading, LOCATION_HEADING)
        self.assertEqual(len(result.groups), 3)
