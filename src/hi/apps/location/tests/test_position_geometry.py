"""
Tests for PositionGeometry.

Pure-functional layout math. No DB writes; some methods take a
``LocationView`` (mockable) or a Location row.
"""

import logging
from decimal import Decimal
from unittest.mock import Mock

from hi.apps.entity.models import Entity
from hi.apps.entity.enums import EntityType
from hi.apps.location.position_geometry import PositionGeometry
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestPositionGeometryViewCenter(BaseTestCase):

    def test_view_center_respects_origin(self):
        from hi.apps.common.svg_models import SvgViewBox

        location_view = Mock()
        location_view.svg_view_box = SvgViewBox(x=200, y=300, width=1000, height=1000)

        x, y = PositionGeometry.view_center(location_view)
        self.assertAlmostEqual(x, 700.0)
        self.assertAlmostEqual(y, 800.0)


class TestPositionGeometryGridSlot(BaseTestCase):

    def _make_view(self, x, y, width, height):
        from hi.apps.common.svg_models import SvgViewBox

        location_view = Mock()
        location_view.svg_view_box = SvgViewBox(x=x, y=y, width=width, height=height)
        return location_view

    def test_single_entity_returns_center(self):
        view = self._make_view(0, 0, 1000, 1000)
        x, y = PositionGeometry.grid_slot(location_view=view, grid_index=0, grid_total=1)
        self.assertAlmostEqual(x, 500.0)
        self.assertAlmostEqual(y, 500.0)

    def test_multiple_entities_distributed_around_center(self):
        view = self._make_view(0, 0, 1000, 1000)
        positions = [
            PositionGeometry.grid_slot(location_view=view, grid_index=i, grid_total=4)
            for i in range(4)
        ]
        xs = [p[0] for p in positions]
        ys = [p[1] for p in positions]
        self.assertAlmostEqual(xs[0] + xs[3], 1000.0)
        self.assertAlmostEqual(xs[1] + xs[2], 1000.0)
        self.assertEqual(len(set(round(y, 6) for y in ys)), 1)
        self.assertAlmostEqual(ys[0], 500.0)

    def test_grid_wraps_to_multiple_rows(self):
        view = self._make_view(0, 0, 1000, 1000)
        x_0, y_0 = PositionGeometry.grid_slot(location_view=view, grid_index=0, grid_total=8)
        x_4, y_4 = PositionGeometry.grid_slot(location_view=view, grid_index=4, grid_total=8)
        self.assertAlmostEqual(x_0, x_4)
        self.assertLess(y_0, y_4)

    def test_clamps_to_viewbox_margin(self):
        view = self._make_view(0, 0, 100, 100)
        x, y = PositionGeometry.grid_slot(location_view=view, grid_index=0, grid_total=16)
        margin_fraction = PositionGeometry.DEFAULT_VIEWBOX_MARGIN_FRACTION
        margin = 100 * margin_fraction
        self.assertGreaterEqual(x, margin)
        self.assertLessEqual(x, 100 - margin)
        self.assertGreaterEqual(y, margin)
        self.assertLessEqual(y, 100 - margin)


class TestPositionGeometryDefaultIconScale(BaseTestCase):

    def _fixtures(self, viewbox_width, viewbox_height):
        from hi.apps.common.svg_models import SvgViewBox
        from hi.apps.location.models import Location

        entity = Entity.objects.create(
            name='Scale Test Entity',
            entity_type_str=str(EntityType.CAMERA),
        )
        location = Location.objects.create(
            name='Test Location',
            svg_view_box_str=f'0 0 {viewbox_width} {viewbox_height}',
        )
        location_view = Mock()
        location_view.location = location
        location_view.svg_view_box = SvgViewBox(
            x=0, y=0, width=viewbox_width, height=viewbox_height,
        )
        return entity, location, location_view

    def test_zero_viewbox_clamps_to_min_scale(self):
        entity, location, location_view = self._fixtures(0, 0)
        scale = PositionGeometry.default_icon_scale(
            entity=entity, location_view=location_view,
        )
        self.assertEqual(scale, Decimal(str(location.svg_position_bounds.min_scale)))

    def test_very_large_viewbox_clamps_to_max_scale(self):
        entity, location, location_view = self._fixtures(100000, 100000)
        scale = PositionGeometry.default_icon_scale(
            entity=entity, location_view=location_view,
        )
        self.assertEqual(scale, Decimal(str(location.svg_position_bounds.max_scale)))

    def test_very_small_viewbox_clamps_to_min_scale(self):
        entity, location, location_view = self._fixtures(10, 10)
        scale = PositionGeometry.default_icon_scale(
            entity=entity, location_view=location_view,
        )
        self.assertEqual(scale, Decimal(str(location.svg_position_bounds.min_scale)))


class TestPositionGeometryPathCenter(BaseTestCase):

    def test_path_center_averages_extracted_coords(self):
        # Square corners: average is the center.
        x, y = PositionGeometry.path_center('M 0,0 L 10,0 L 10,10 L 0,10 Z')
        self.assertAlmostEqual(x, 5.0)
        self.assertAlmostEqual(y, 5.0)

    def test_path_center_returns_none_for_empty(self):
        self.assertEqual(PositionGeometry.path_center(''), (None, None))

    def test_path_center_returns_none_for_too_few_coords(self):
        # Single point: 2 numbers, below the 4-number minimum.
        self.assertEqual(PositionGeometry.path_center('M 5,5'), (None, None))

    def test_path_center_handles_negative_and_decimal_coords(self):
        x, y = PositionGeometry.path_center('M -10,-5 L 10,5')
        self.assertAlmostEqual(x, 0.0)
        self.assertAlmostEqual(y, 0.0)
