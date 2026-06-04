"""
Tests for PositionGeometry.

Pure-functional layout math. No DB writes and no model coupling:
methods take a bare ``SvgViewBox`` and return geometry.
"""

import logging
from decimal import Decimal

from hi.apps.common.svg_models import SvgItemPositionBounds, SvgViewBox
from hi.apps.entity.models import Entity
from hi.apps.entity.enums import EntityType
from hi.apps.location.position_geometry import PositionGeometry
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestPositionGeometryViewCenter(BaseTestCase):

    def test_view_center_respects_origin(self):
        view_box = SvgViewBox(x=200, y=300, width=1000, height=1000)
        x, y = PositionGeometry.view_center(view_box)
        self.assertAlmostEqual(x, 700.0)
        self.assertAlmostEqual(y, 800.0)


class TestPositionGeometryGridSlot(BaseTestCase):

    def test_single_entity_returns_center(self):
        view_box = SvgViewBox(x=0, y=0, width=1000, height=1000)
        x, y = PositionGeometry.grid_slot(view_box=view_box, grid_index=0, grid_total=1)
        self.assertAlmostEqual(x, 500.0)
        self.assertAlmostEqual(y, 500.0)

    def test_multiple_entities_distributed_around_center(self):
        view_box = SvgViewBox(x=0, y=0, width=1000, height=1000)
        positions = [
            PositionGeometry.grid_slot(view_box=view_box, grid_index=i, grid_total=4)
            for i in range(4)
        ]
        # All four positions are distinct, all sit inside the viewbox
        # margin, and the distribution is symmetric around the view
        # center (mean position equals center). Specific grid shape
        # (2x2 vs 1x4) is an implementation detail of the column-count
        # adaptation and is not asserted.
        self.assertEqual(len(set(positions)), 4)
        margin = 1000 * PositionGeometry.DEFAULT_VIEWBOX_MARGIN_FRACTION
        for x, y in positions:
            self.assertGreaterEqual(x, margin)
            self.assertLessEqual(x, 1000 - margin)
            self.assertGreaterEqual(y, margin)
            self.assertLessEqual(y, 1000 - margin)
        mean_x = sum(p[0] for p in positions) / len(positions)
        mean_y = sum(p[1] for p in positions) / len(positions)
        self.assertAlmostEqual(mean_x, 500.0)
        self.assertAlmostEqual(mean_y, 500.0)

    def test_grid_wraps_to_multiple_rows(self):
        view_box = SvgViewBox(x=0, y=0, width=1000, height=1000)
        positions = [
            PositionGeometry.grid_slot(view_box=view_box, grid_index=i, grid_total=8)
            for i in range(8)
        ]
        # Grid spans multiple rows AND multiple columns (eight items
        # cannot fit in a single row or single column at the default
        # adaptive shape).
        distinct_xs = {round(p[0], 6) for p in positions}
        distinct_ys = {round(p[1], 6) for p in positions}
        self.assertGreater(len(distinct_xs), 1)
        self.assertGreater(len(distinct_ys), 1)

    def test_clamps_to_viewbox_margin(self):
        view_box = SvgViewBox(x=0, y=0, width=100, height=100)
        x, y = PositionGeometry.grid_slot(view_box=view_box, grid_index=0, grid_total=16)
        margin_fraction = PositionGeometry.DEFAULT_VIEWBOX_MARGIN_FRACTION
        margin = 100 * margin_fraction
        self.assertGreaterEqual(x, margin)
        self.assertLessEqual(x, 100 - margin)
        self.assertGreaterEqual(y, margin)
        self.assertLessEqual(y, 100 - margin)


class TestPositionGeometryDefaultIconScale(BaseTestCase):

    def _fixtures(self, viewbox_width, viewbox_height):
        entity = Entity.objects.create(
            name='Scale Test Entity',
            entity_type_str=str(EntityType.CAMERA),
        )
        view_box = SvgViewBox(x=0, y=0, width=viewbox_width, height=viewbox_height)
        return entity, view_box

    def test_zero_viewbox_clamps_to_min_scale(self):
        entity, view_box = self._fixtures(0, 0)
        scale = PositionGeometry.default_icon_scale(entity=entity, view_box=view_box)
        self.assertEqual(scale, Decimal(str(SvgItemPositionBounds.DEFAULT_MIN_SCALE)))

    def test_very_large_viewbox_clamps_to_max_scale(self):
        entity, view_box = self._fixtures(100000, 100000)
        scale = PositionGeometry.default_icon_scale(entity=entity, view_box=view_box)
        self.assertEqual(scale, Decimal(str(SvgItemPositionBounds.DEFAULT_MAX_SCALE)))

    def test_very_small_viewbox_clamps_to_min_scale(self):
        entity, view_box = self._fixtures(10, 10)
        scale = PositionGeometry.default_icon_scale(entity=entity, view_box=view_box)
        self.assertEqual(scale, Decimal(str(SvgItemPositionBounds.DEFAULT_MIN_SCALE)))


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
