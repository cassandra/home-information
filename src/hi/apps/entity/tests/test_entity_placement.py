"""
Tests for EntityPlacementCalculator and EntityPlacer.

The pure layout math (grid slots, viewbox margin clamping, default
icon scale) is owned by ``PositionGeometry`` and exercised in
``hi/apps/location/tests/test_position_geometry.py``. This file
exercises the placement-layer responsibilities:

* Calculator entity-routing: deciding shape kind per entity, single
  vs. bulk dispatch.
* Placer persistence: idempotent EntityPosition creation via the
  shape-dispatching path.
"""

import logging
from decimal import Decimal
from unittest.mock import Mock

from hi.apps.entity.entity_placement import (
    EntityPlacementCalculator,
    EntityPlacer,
    PlacementPoint,
)
from hi.apps.entity.models import Entity, EntityPosition
from hi.apps.entity.enums import EntityType
from hi.apps.location.position_geometry import PositionGeometry
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestEntityPlacerPersistence(BaseTestCase):
    """Persistence behavior: persisting a PlacementPoint creates an
    EntityPosition centered on the viewbox and is idempotent on
    re-call."""

    def test_persists_centered_position(self):
        from hi.apps.location.models import Location
        from hi.apps.common.svg_models import SvgViewBox

        entity = Entity.objects.create(
            name='Position Test Entity',
            entity_type_str=str(EntityType.CAMERA),
            integration_id='pos_test_001',
            integration_name='test_integration',
        )
        location = Location.objects.create(
            name='Test Location',
            svg_view_box_str='100 200 400 300',
        )
        view_box = SvgViewBox(x=100, y=200, width=400, height=300)
        location_view = Mock()
        location_view.location = location
        location_view.svg_view_box = view_box

        placer = EntityPlacer()
        # Compute the shape via the calculator, then persist directly
        # (skipping place_entity_in_view to avoid delegate-pairing
        # side effects that need a real EntityView).
        placement_shape = placer.calculator.shape_for_entity(
            entity=entity, location_view=location_view,
        )
        self.assertIsInstance(placement_shape, PlacementPoint)
        placer._persist_placement_shape(
            entity=entity,
            location_view=location_view,
            placement_shape=placement_shape,
        )

        entity_position = EntityPosition.objects.get(
            entity=entity, location=location,
        )
        # Centered on the viewbox: 100 + 400/2 = 300, 200 + 300/2 = 350.
        self.assertEqual(entity_position.svg_x, Decimal('300'))
        self.assertEqual(entity_position.svg_y, Decimal('350'))
        # Default icon size is a percentage of the viewbox's smaller dimension.
        expected_scale = (
            Decimal('300')
            * Decimal(str(PositionGeometry.DEFAULT_ICON_SIZE_PERCENT_OF_VIEWBOX))
            / Decimal('100')
            / Decimal('64')
        )
        self.assertEqual(entity_position.svg_scale, expected_scale)
        self.assertEqual(entity_position.svg_rotate, Decimal('0.0'))

        # Re-call must not create a duplicate row.
        placer._persist_placement_shape(
            entity=entity,
            location_view=location_view,
            placement_shape=placement_shape,
        )
        position_count = EntityPosition.objects.filter(
            entity=entity, location=location,
        ).count()
        self.assertEqual(position_count, 1)


class TestEntityPlacementCalculatorBulkShapes(BaseTestCase):
    """shapes_for_entities returns one shape per entity in input
    order, computed against a single grid pass over the whole group.
    The grid math itself is tested in test_position_geometry; this
    class verifies the calculator's entity-routing wrapper."""

    def _make_location_view(self):
        from hi.apps.common.svg_models import SvgViewBox
        from hi.apps.location.models import Location

        location = Location.objects.create(
            name='Bulk Test Location',
            svg_view_box_str='0 0 1000 1000',
        )
        location_view = Mock()
        location_view.location = location
        location_view.svg_view_box = SvgViewBox(x=0, y=0, width=1000, height=1000)
        return location_view

    def test_empty_input_yields_empty_shapes(self):
        calculator = EntityPlacementCalculator()
        location_view = self._make_location_view()
        self.assertEqual(
            calculator.shapes_for_entities(entities=[], location_view=location_view),
            [],
        )

    def test_single_entity_falls_back_to_single_shape(self):
        calculator = EntityPlacementCalculator()
        location_view = self._make_location_view()
        entity = Entity.objects.create(
            name='Single Camera',
            entity_type_str=str(EntityType.CAMERA),
        )
        shapes = calculator.shapes_for_entities(
            entities=[entity], location_view=location_view,
        )
        self.assertEqual(len(shapes), 1)
        self.assertIsInstance(shapes[0], PlacementPoint)
        # Centered on viewbox.
        self.assertAlmostEqual(shapes[0].svg_x, 500.0)
        self.assertAlmostEqual(shapes[0].svg_y, 500.0)

    def test_multiple_icon_entities_each_get_a_grid_slot(self):
        calculator = EntityPlacementCalculator()
        location_view = self._make_location_view()
        entities = [
            Entity.objects.create(
                name=f'Cam {i}',
                entity_type_str=str(EntityType.CAMERA),
                integration_id=f'cam_{i}',
                integration_name='test',
            )
            for i in range(4)
        ]
        shapes = calculator.shapes_for_entities(
            entities=entities, location_view=location_view,
        )
        self.assertEqual(len(shapes), len(entities))
        for shape in shapes:
            self.assertIsInstance(shape, PlacementPoint)
        # Distinct x positions in a single row.
        xs = [s.svg_x for s in shapes]
        self.assertEqual(len(set(xs)), 4)


class TestEntityPlacerSetEntityPath(BaseTestCase):
    """User-drawn-path persistence: creates a new EntityPath row when
    none exists, updates in place when one does."""

    def _entity_and_location(self):
        from hi.apps.location.models import Location
        entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str=str(EntityType.ELECTRIC_WIRE),
            integration_id='wire_001',
            integration_name='test_integration',
        )
        location = Location.objects.create(name='Test Location')
        return entity, location

    def test_set_entity_path_creates_new_when_absent(self):
        from hi.apps.entity.models import EntityPath
        entity, location = self._entity_and_location()

        svg_path_str = 'M 10 10 L 20 20'
        entity_path = EntityPlacer().set_entity_path(
            entity_id=entity.id,
            location=location,
            svg_path_str=svg_path_str,
        )

        self.assertEqual(entity_path.entity, entity)
        self.assertEqual(entity_path.location, location)
        self.assertEqual(entity_path.svg_path, svg_path_str)
        self.assertEqual(
            EntityPath.objects.filter(entity=entity, location=location).count(),
            1,
        )

    def test_set_entity_path_updates_existing_in_place(self):
        from hi.apps.entity.models import EntityPath
        entity, location = self._entity_and_location()

        initial = EntityPath.objects.create(
            entity=entity, location=location, svg_path='M 10 10 L 20 20',
        )
        initial_id = initial.id

        updated_path = 'M 30 30 L 40 40 L 50 50'
        updated = EntityPlacer().set_entity_path(
            entity_id=entity.id,
            location=location,
            svg_path_str=updated_path,
        )

        # Same row, new svg_path; no duplicate row created.
        self.assertEqual(updated.id, initial_id)
        self.assertEqual(updated.svg_path, updated_path)
        self.assertEqual(
            EntityPath.objects.filter(entity=entity, location=location).count(),
            1,
        )
